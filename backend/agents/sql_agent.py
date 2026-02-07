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
    "fact_realtime_congestion_area",
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
fact_store_area_qtr(area_id FK, qtr TEXT, cat_id FK, store_cnt INT, open_cnt INT, close_cnt INT)
  → store_cnt = 해당 분기 영업 중 점포 수 (THIS is the number of stores/cafes!)
  → open_cnt = 신규 개업 점포 수
  → close_cnt = 폐업 점포 수
fact_realtime_congestion_area(area_id FK, ts TIMESTAMPTZ, congestion_level TEXT, ppltn_min INT, ppltn_max INT)
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

## Time-based Analysis (시간대/요일/연령/성별 분석)

fact_flow_area_qtr has JSONB columns for detailed breakdown:
- flow_by_hour: {"0": 1234, "1": 567, ..., "23": 890} — 시간대별 유동인구
- flow_by_weekday: {"월": 1234, "화": 567, ...} — 요일별 유동인구
- flow_by_demo: {"male_10": N, "male_20": N, "female_20": N, ...} — 성별×연령대 유동인구

To query hourly data:
SELECT da.area_name,
       (f.flow_by_hour->>'14')::int AS hour_14,
       (f.flow_by_hour->>'15')::int AS hour_15
FROM fact_flow_area_qtr f
JOIN dim_area da ON f.area_id = da.area_id
WHERE f.qtr = '20244' AND f.area_id IN (SELECT area_id FROM preset_area_scope)

To find peak hours:
SELECT da.area_name, key AS hour, value::int AS flow
FROM fact_flow_area_qtr f
JOIN dim_area da ON f.area_id = da.area_id,
LATERAL jsonb_each_text(f.flow_by_hour) AS x(key, value)
WHERE f.qtr = '20244' AND f.area_id IN (SELECT area_id FROM preset_area_scope)
ORDER BY value::int DESC
LIMIT 10

To query demographic data:
SELECT da.area_name,
       (f.flow_by_demo->>'female_20')::int AS female_20s,
       (f.flow_by_demo->>'female_30')::int AS female_30s
FROM fact_flow_area_qtr f
JOIN dim_area da ON f.area_id = da.area_id
WHERE f.qtr = '20244' AND f.area_id IN (SELECT area_id FROM preset_area_scope)

## Risk Analysis (리스크 분석)

For risk/closure analysis, JOIN fact_store with fact_sales:
SELECT da.area_name,
       fst.store_cnt, fst.close_cnt, fst.open_cnt,
       ROUND(fst.close_cnt::numeric / NULLIF(fst.store_cnt, 0) * 100, 1) AS close_rate_pct,
       fs.sales_amt
FROM fact_store_area_qtr fst
JOIN dim_area da ON fst.area_id = da.area_id
LEFT JOIN fact_sales_area_qtr fs ON fs.area_id = fst.area_id AND fs.qtr = fst.qtr
WHERE fst.qtr = '20251' AND fst.area_id IN (SELECT area_id FROM preset_area_scope)

## Latest Available Quarters
- Sales (fact_sales_area_qtr): 20251 (latest), 20244, 20243, 20242, 20241...
- Flow (fact_flow_area_qtr): 20244 (latest), 20243, 20242, 20241
- Store (fact_store_area_qtr): 20251 (latest), 20244, 20243, 20242

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
