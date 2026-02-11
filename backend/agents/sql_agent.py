"""SQL Agent — generates, validates, and executes SQL from natural language."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from langchain_openai import ChatOpenAI
from sqlalchemy import text

from db import engine

ALLOWED_TABLES = {
    "dim_area",
    "dim_category",
    "fact_sales_area_qtr",
    "fact_flow_area_qtr",
    "fact_store_area_qtr",
    "fact_facility_area_qtr",
    "fact_realtime_congestion_area",
    "fact_social_trend_daily",
    "social_module_config",
    "bridge_area_h3_weight",
    "preset_area_scope",
}

FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

SQL_SYSTEM_PROMPT = """\
You are a SQL generation agent for a 성수동 commercial district analysis DB (PostgreSQL + PostGIS).

## Allowed tables and key columns

dim_area(area_id PK, area_type TEXT ['ADMIN_DONG','COMMERCIAL_AREA'], area_code TEXT, area_name TEXT, geom GEOMETRY)
dim_category(cat_id PK, service_code TEXT, service_name TEXT)
fact_sales_area_qtr(area_id FK, qtr TEXT 'YYYYQ', cat_id FK, sales_amt NUMERIC, sales_cnt INT, confidence_score NUMERIC)
  → sales_amt = 분기 총 매출액 (단위: 원)
  → sales_cnt = 분기 총 거래 건수 (NOT 점포수!)
fact_flow_area_qtr(area_id FK, qtr TEXT, flow_total INT, flow_by_hour JSONB, flow_by_weekday JSONB, flow_by_demo JSONB)
  → flow_total = 분기 총 유동인구 수
  → flow_by_demo JSONB structure: {"male": <int>, "female": <int>, "age_10": <int>, "age_20": <int>, "age_30": <int>, "age_40": <int>, "age_50": <int>, "age_60+": <int>}
  → flow_by_weekday JSONB structure: {"mon": <int>, "tue": <int>, "wed": <int>, "thu": <int>, "fri": <int>, "sat": <int>, "sun": <int>}
  → flow_by_hour JSONB structure: {"00_06": <int>, "06_11": <int>, "11_14": <int>, "14_17": <int>, "17_21": <int>, "21_24": <int>}
fact_store_area_qtr(area_id FK, qtr TEXT, cat_id FK, store_cnt INT, open_cnt INT, close_cnt INT)
  → store_cnt = 해당 분기 영업 중 점포 수 (THIS is the number of stores/cafes!)
  → open_cnt = 신규 개업 점포 수
  → close_cnt = 폐업 점포 수
fact_realtime_congestion_area(area_id FK, ts TIMESTAMPTZ, congestion_level TEXT, ppltn_min INT, ppltn_max INT)
fact_facility_area_qtr(area_id FK, qtr TEXT, facility_type TEXT, facility_cnt INT)
  → 상권별 집객시설 건수 (narrow/EAV 포맷: 시설 유형별 1행)
  → facility_type 코드: VIATR_FCLTY(관광시설), PBLOFC(관공서), BANK(은행), GEHSPT(종합병원), GNRL_HSPTL(일반병원),
    PARMACY(약국), KNDRGR(유치원), ELESCH(초등학교), MSKUL(중학교), HGSCHL(고등학교), UNIV(대학교),
    DRTS(백화점), SUPMK(대형마트), THEAT(극장), STAYNG_FCLTY(숙박시설), ARPRT(공항),
    RLROAD_STATN(철도역), BUS_TRMINL(버스터미널), SUBWAY_STATN(지하철역), BUS_STTN(버스정류장)
fact_social_trend_daily(trend_id PK, area_id FK NULLABLE, source TEXT ['youtube','naver_blog','naver_cafe'], collected_date DATE, keyword TEXT, buzz_volume INT, sentiment_score NUMERIC, sentiment_pos INT, sentiment_neg INT, top_keywords JSONB, evidence_snippets JSONB)
  → area_id NULL = 성수동 전체, NOT NULL = 상권 수준 매핑
  → source: youtube, naver_blog, naver_cafe
  → buzz_volume: 해당 날짜 콘텐츠 수
  → sentiment_score: -1.0 ~ 1.0
social_module_config(config_key PK, config_value TEXT, updated_at TIMESTAMPTZ)
bridge_area_h3_weight(area_id FK, h3_index TEXT, weight NUMERIC)
preset_area_scope(area_id FK) — 성수동 프리셋 필터

## CRITICAL: Per-Store and Per-Day Calculations

When user asks for "점포당", "카페당", "1개 기준", "개별 점포" calculations:
- MUST JOIN fact_store_area_qtr to get store_cnt
- Formula: sales_amt / NULLIF(store_cnt, 0) AS sales_per_store

When user asks for "1일", "하루", "일 평균" calculations:
- One quarter = 90 days (approximate)
- Formula: sales_amt / 90 AS daily_sales
- For per-store daily: sales_amt / NULLIF(store_cnt, 0) / 90 AS daily_sales_per_store

Example for "카페별 1일 매출":
SELECT 
    da.area_name,
    fs.sales_amt AS quarterly_sales,
    fst.store_cnt,
    ROUND(fs.sales_amt / NULLIF(fst.store_cnt, 0) / 90) AS daily_sales_per_store
FROM fact_sales_area_qtr fs
JOIN dim_area da ON fs.area_id = da.area_id
JOIN dim_category dc ON fs.cat_id = dc.cat_id
JOIN fact_store_area_qtr fst ON fs.area_id = fst.area_id AND fs.qtr = fst.qtr AND fs.cat_id = fst.cat_id
WHERE dc.service_name = '커피-음료' 
  AND fs.qtr = '20251' 
  AND fs.area_id IN (SELECT area_id FROM preset_area_scope)
ORDER BY daily_sales_per_store DESC

## WARNING: sales_cnt vs store_cnt
- sales_cnt (fact_sales) = 거래 건수 (number of transactions)
- store_cnt (fact_store) = 점포 수 (number of stores)
These are DIFFERENT! Do NOT confuse them.

## IMPORTANT: For 창업 추천 (suitability) queries
To find good locations for a business, JOIN multiple fact tables:
- fact_sales_area_qtr for 매출
- fact_flow_area_qtr for 유동인구
- fact_store_area_qtr for 경쟁 점포수
Example pattern:
SELECT da.area_name, fs.sales_amt, ff.flow_total, fst.store_cnt
FROM fact_sales_area_qtr fs
JOIN dim_area da ON fs.area_id = da.area_id
JOIN dim_category dc ON fs.cat_id = dc.cat_id
LEFT JOIN fact_flow_area_qtr ff ON fs.area_id = ff.area_id AND fs.qtr = ff.qtr
LEFT JOIN fact_store_area_qtr fst ON fs.area_id = fst.area_id AND fs.qtr = fst.qtr AND fs.cat_id = fst.cat_id
WHERE dc.service_name = '...' AND fs.qtr = '20251' AND fs.area_id IN (SELECT area_id FROM preset_area_scope)
ORDER BY fs.sales_amt DESC

## Category Name Mapping (IMPORTANT!)
Users may use colloquial terms. Map to actual service_name in dim_category:
- 커피, 카페, 커피전문점, 커피 전문점 → '커피-음료'
- 디저트, 디저트카페, 베이커리 → '제과점'
- 치킨, 치킨집 → '치킨전문점'
- 호프, 맥주, 주점, 술집 → '호프-간이주점'
- 분식, 떡볶이 → '분식전문점'
- 한식, 한식당 → '한식음식점'
- 중식, 중국집 → '중식음식점'
- 일식, 초밥 → '일식음식점'
- 양식 → '양식음식점'
- 패스트푸드, 햄버거 → '패스트푸드점'
- 편의점 → '편의점'
- 미용실, 헤어샵 → '미용실'
- 네일, 네일샵 → '네일숍'
- PC방, 피씨방 → 'PC방'

When querying categories, use the exact service_name from above or use LIKE pattern matching.

## IMPORTANT: Demographic (인구통계) Queries using flow_by_demo JSONB

To extract demographic data from flow_by_demo JSONB, use PostgreSQL ->> operator.
CRITICAL: JSONB values are stored as floats (e.g., "191521.0"), so you MUST cast to ::numeric, NOT ::int.

- Gender: (flow_by_demo->>'male')::numeric, (flow_by_demo->>'female')::numeric
- Age: (flow_by_demo->>'age_10')::numeric, (flow_by_demo->>'age_20')::numeric, ... (flow_by_demo->>'age_60+')::numeric
- Weekday: (flow_by_weekday->>'mon')::numeric, etc.

Example: "20대 여성 유동인구 Top3 상권"
SELECT da.area_name,
       ff.flow_total,
       (ff.flow_by_demo->>'female')::numeric AS female_flow,
       (ff.flow_by_demo->>'age_20')::numeric AS age20_flow,
       ROUND((ff.flow_by_demo->>'female')::numeric / NULLIF(ff.flow_total, 0) * (ff.flow_by_demo->>'age_20')::numeric / NULLIF(ff.flow_total, 0) * ff.flow_total) AS target_flow
FROM fact_flow_area_qtr ff
JOIN dim_area da ON ff.area_id = da.area_id
WHERE ff.qtr = '20244'
  AND ff.area_id IN (SELECT area_id FROM preset_area_scope)
ORDER BY target_flow DESC
LIMIT 3

Example: "요일별 유동인구" (flow_by_weekday JSONB)
SELECT da.area_name,
       (ff.flow_by_weekday->>'mon')::numeric AS mon,
       (ff.flow_by_weekday->>'tue')::numeric AS tue,
       (ff.flow_by_weekday->>'wed')::numeric AS wed,
       (ff.flow_by_weekday->>'thu')::numeric AS thu,
       (ff.flow_by_weekday->>'fri')::numeric AS fri,
       (ff.flow_by_weekday->>'sat')::numeric AS sat,
       (ff.flow_by_weekday->>'sun')::numeric AS sun
FROM fact_flow_area_qtr ff
JOIN dim_area da ON ff.area_id = da.area_id
WHERE ff.qtr = '20244' AND ff.area_id IN (SELECT area_id FROM preset_area_scope)

## IMPORTANT: Facility (집객시설) Queries

fact_facility_area_qtr is in narrow/EAV format: each (area_id, qtr, facility_type) is one row.
To get total facility count for an area, SUM facility_cnt.
To get specific facility types, filter by facility_type code.

Example: "지하철역, 버스정류장이 가장 많은 상권"
SELECT da.area_name,
       SUM(CASE WHEN facility_type = 'SUBWAY_STATN' THEN facility_cnt ELSE 0 END) AS subway,
       SUM(CASE WHEN facility_type = 'BUS_STTN' THEN facility_cnt ELSE 0 END) AS bus_stop,
       SUM(facility_cnt) AS total_facilities
FROM fact_facility_area_qtr fac
JOIN dim_area da ON fac.area_id = da.area_id
WHERE fac.qtr = '20253'
  AND fac.area_id IN (SELECT area_id FROM preset_area_scope)
GROUP BY da.area_name
ORDER BY total_facilities DESC
LIMIT 5

Facility type mapping (code → 한글):
VIATR_FCLTY=관광시설, PBLOFC=관공서, BANK=은행, GEHSPT=종합병원, GNRL_HSPTL=일반병원,
PARMACY=약국, KNDRGR=유치원, ELESCH=초등학교, MSKUL=중학교, HGSCHL=고등학교, UNIV=대학교,
DRTS=백화점, SUPMK=대형마트, THEAT=극장, STAYNG_FCLTY=숙박시설, ARPRT=공항,
RLROAD_STATN=철도역, BUS_TRMINL=버스터미널, SUBWAY_STATN=지하철역, BUS_STTN=버스정류장

## Latest Available Quarters
- Sales (fact_sales_area_qtr): 20251 (latest), 20244, 20243, 20242, 20241...
- Flow (fact_flow_area_qtr): 20244 (latest), 20243, 20242, 20241
- Store (fact_store_area_qtr): 20251 (latest), 20244, 20243, 20242
- Facility (fact_facility_area_qtr): 20253 (latest), 20252, 20251, 20244...

## Quarter Comparison Queries (비교/대비/변화/전분기/전년동기/증감)

When user asks about comparison between two quarters, use WITH CTE pattern:

Example 1: 단일 지표 비교 (매출 변화율)
WITH before_q AS (
    SELECT da.area_name, SUM(fs.sales_amt) AS sales_amt
    FROM fact_sales_area_qtr fs
    JOIN dim_area da ON fs.area_id = da.area_id
    JOIN dim_category dc ON fs.cat_id = dc.cat_id
    WHERE dc.service_name = '커피-음료' AND fs.qtr = '20243'
      AND fs.area_id IN (SELECT area_id FROM preset_area_scope)
    GROUP BY da.area_name
),
after_q AS (
    SELECT da.area_name, SUM(fs.sales_amt) AS sales_amt
    FROM fact_sales_area_qtr fs
    JOIN dim_area da ON fs.area_id = da.area_id
    JOIN dim_category dc ON fs.cat_id = dc.cat_id
    WHERE dc.service_name = '커피-음료' AND fs.qtr = '20244'
      AND fs.area_id IN (SELECT area_id FROM preset_area_scope)
    GROUP BY da.area_name
)
SELECT b.area_name,
       b.sales_amt AS before_sales,
       a.sales_amt AS after_sales,
       ROUND((a.sales_amt - b.sales_amt) / NULLIF(b.sales_amt, 0) * 100, 1) AS change_pct
FROM before_q b
JOIN after_q a ON b.area_name = a.area_name
ORDER BY change_pct DESC
LIMIT 20

Example 2: 복합 비교 (매출 + 유동인구)
WITH before_q AS (
    SELECT fs.area_id, da.area_name, SUM(fs.sales_amt) AS sales_amt, ff.flow_total
    FROM fact_sales_area_qtr fs
    JOIN dim_area da ON fs.area_id = da.area_id
    LEFT JOIN fact_flow_area_qtr ff ON fs.area_id = ff.area_id AND ff.qtr = '20243'
    WHERE fs.qtr = '20243' AND fs.area_id IN (SELECT area_id FROM preset_area_scope)
    GROUP BY fs.area_id, da.area_name, ff.flow_total
),
after_q AS (
    SELECT fs.area_id, da.area_name, SUM(fs.sales_amt) AS sales_amt, ff.flow_total
    FROM fact_sales_area_qtr fs
    JOIN dim_area da ON fs.area_id = da.area_id
    LEFT JOIN fact_flow_area_qtr ff ON fs.area_id = ff.area_id AND ff.qtr = '20244'
    WHERE fs.qtr = '20244' AND fs.area_id IN (SELECT area_id FROM preset_area_scope)
    GROUP BY fs.area_id, da.area_name, ff.flow_total
)
SELECT b.area_name,
       ROUND((a.sales_amt - b.sales_amt) / NULLIF(b.sales_amt, 0) * 100, 1) AS sales_change_pct,
       ROUND((a.flow_total - b.flow_total) / NULLIF(b.flow_total, 0) * 100, 1) AS flow_change_pct
FROM before_q b
JOIN after_q a ON b.area_id = a.area_id
ORDER BY sales_change_pct DESC
LIMIT 20

Comparison keywords: 대비, 비교, 변화, 전분기, 전년동기, 증감, 증가, 감소, 전 분기, 이전 분기

## Rules
1. SELECT only. No DDL/DML.
2. Always filter to 성수동 using: WHERE area_id IN (SELECT area_id FROM preset_area_scope)
3. Default time range: use the latest available quarter for each table.
4. Always include LIMIT (max 200).
5. Return ONLY the SQL query, no explanation.
6. When joining fact tables with dim_category, always use: JOIN dim_category dc ON ... WHERE dc.service_name = '...'
"""


def _validate_sql(sql: str) -> str | None:
    """Return an error message if SQL is invalid, else None."""
    stripped = sql.strip().rstrip(";").strip()
    if not stripped.upper().startswith("SELECT"):
        return "Only SELECT statements are allowed."
    if FORBIDDEN_KEYWORDS.search(stripped):
        return "Forbidden SQL keyword detected."
    # Check table whitelist — extract FROM/JOIN table references
    table_pattern = re.compile(
        r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE
    )
    tables_used = {t.lower() for t in table_pattern.findall(stripped)}
    disallowed = tables_used - ALLOWED_TABLES
    if disallowed:
        return f"Access to table(s) not allowed: {disallowed}"
    return None


def _ensure_limit(sql: str) -> str:
    """Append LIMIT 200 if no LIMIT clause exists."""
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = sql.rstrip().rstrip(";") + " LIMIT 200"
    return sql


def sql_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: generate SQL, validate, execute, return results."""
    question = state["question"]
    messages_history = state.get("messages", [])
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # Build conversation context
    llm_messages = [{"role": "system", "content": SQL_SYSTEM_PROMPT}]
    
    # Add conversation history (last 6 messages for context)
    for msg in messages_history[-6:]:
        llm_messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current question
    llm_messages.append({"role": "user", "content": question})

    response = llm.invoke(llm_messages)
    sql = response.content.strip()
    # Strip markdown code fences if present
    if sql.startswith("```"):
        sql = re.sub(r"^```(?:sql)?\n?", "", sql)
        sql = re.sub(r"\n?```$", "", sql)
    sql = sql.strip()

    # Validate
    error = _validate_sql(sql)
    if error:
        return {
            "sql_text": sql,
            "sql_result": f"[BLOCKED] {error}",
            "data_asof": None,
        }

    sql = _ensure_limit(sql)

    # Execute
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql))
            columns = list(rows.keys())
            data = [dict(zip(columns, row)) for row in rows.fetchall()]
        result = {"columns": columns, "rows": data, "row_count": len(data)}
    except Exception as exc:
        result = f"[SQL_ERROR] {exc}"

    now = datetime.now()
    return {
        "sql_text": sql,
        "sql_result": result,
        "data_asof": now.strftime("%Y-%m-%d %H:%M"),
    }
