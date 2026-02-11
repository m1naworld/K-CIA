"""Social API — GET /api/social/trends and /api/social/config."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from db import engine

router = APIRouter(prefix="/api/social", tags=["social"])

# dim_category service_name 키워드 → Gemini 태거 카테고리 라벨
# ETL 시점에 Gemini Flash가 태깅한 matched_categories 컬럼 필터에 사용
SERVICE_TO_SOCIAL_CATEGORY: dict[str, list[str]] = {
    "커피": ["커피", "음료"],
    "음료": ["음료", "커피"],
    "한식": ["한식"],
    "중식": ["중식"],
    "일식": ["일식"],
    "양식": ["양식"],
    "치킨": ["치킨"],
    "분식": ["분식"],
    "패스트푸드": ["패스트푸드"],
    "호프": ["호프"],
    "제과": ["제과"],
    "의류": ["의류"],
    "화장품": ["화장품"],
    "미용": ["미용"],
    "인테리어": ["인테리어"],
    "갤러리": ["갤러리"],
    "팝업": ["팝업"],
    "편집샵": ["편집샵"],
    "서점": ["서점"],
    "운동": ["운동"],
}


# ---------- Schemas ----------

class SocialConfigResponse(BaseModel):
    enabled: bool
    youtube_enabled: bool
    naver_enabled: bool
    default_keywords: list[str]
    collection_days: int


class SourceBreakdown(BaseModel):
    source: str
    count: int
    buzz: int


class TrendDayPoint(BaseModel):
    date: str
    buzz: int


class EvidenceSnippet(BaseModel):
    title: str = ""
    url: str = ""
    published_at: str = ""
    snippet: str = ""
    source: str = ""
    keyword: str = ""


class SocialTrendsResponse(BaseModel):
    total_buzz: int
    avg_sentiment: float | None
    total_pos: int
    total_neg: int
    by_source: list[SourceBreakdown]
    top_keywords: list[str]
    evidence_snippets: list[EvidenceSnippet]
    daily_trend: list[TrendDayPoint]
    data_asof: str
    filtered_area: str | None = None
    filtered_category: str | None = None
    is_fallback: bool = False


# ---------- Endpoints ----------

@router.get("/config", response_model=SocialConfigResponse)
async def get_social_config() -> SocialConfigResponse:
    """Get social module configuration (ON/OFF state)."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT config_key, config_value FROM social_module_config")
        )
        config = {row[0]: row[1] for row in result}

    keywords = []
    try:
        keywords = json.loads(config.get("default_keywords", "[]"))
    except (json.JSONDecodeError, TypeError):
        pass

    return SocialConfigResponse(
        enabled=config.get("enabled", "false").lower() == "true",
        youtube_enabled=config.get("youtube_enabled", "false").lower() == "true",
        naver_enabled=config.get("naver_enabled", "false").lower() == "true",
        default_keywords=keywords,
        collection_days=int(config.get("collection_days", "30")),
    )


@router.get("/trends", response_model=SocialTrendsResponse)
async def get_social_trends(
    days: int = Query(30, ge=1, le=365, description="Look back N days"),
    source: str | None = Query(None, description="Filter by source"),
    keyword: str | None = Query(None, description="Filter by keyword"),
    area_id: int | None = Query(None, description="Filter by area_id"),
    h3_index: str | None = Query(None, description="Filter by H3 (→ area_ids)"),
    cat_code: str | None = Query(None, description="Filter by category code"),
) -> SocialTrendsResponse:
    """Get aggregated social trend data."""
    conditions = ["collected_date >= current_date - :days"]
    params: dict = {"days": days}

    if source:
        conditions.append("source = :source")
        params["source"] = source
    if keyword:
        conditions.append("keyword ILIKE :keyword")
        params["keyword"] = f"%{keyword}%"

    # --- Resolve h3_index / area_id → area filter ---
    resolved_area_ids: list[int] = []
    filtered_area: str | None = None
    filtered_category: str | None = None

    with engine.connect() as conn:
        if h3_index:
            rows = conn.execute(
                text("""
                    SELECT DISTINCT bw.area_id FROM bridge_area_h3_weight bw
                    JOIN dim_area da ON da.area_id = bw.area_id
                    WHERE bw.h3_index = :h3 AND da.area_type = 'COMMERCIAL_AREA'
                """),
                {"h3": h3_index},
            ).fetchall()
            resolved_area_ids = [r[0] for r in rows]
        elif area_id:
            resolved_area_ids = [area_id]

        # Resolve area name for response context
        if resolved_area_ids:
            name_row = conn.execute(
                text(
                    "SELECT area_name FROM dim_area "
                    "WHERE area_id = ANY(:ids) LIMIT 1"
                ),
                {"ids": resolved_area_ids},
            ).fetchone()
            if name_row:
                filtered_area = name_row[0]

        # --- cat_code → matched_categories filter (Gemini tagged) ---
        social_cats: list[str] = []
        if cat_code:
            cat_row = conn.execute(
                text(
                    "SELECT service_name FROM dim_category "
                    "WHERE service_code = :code"
                ),
                {"code": cat_code},
            ).fetchone()
            if cat_row:
                svc_name = cat_row[0]
                filtered_category = svc_name
                for frag, cats in SERVICE_TO_SOCIAL_CATEGORY.items():
                    if frag in svc_name:
                        social_cats = cats
                        break
                if social_cats:
                    cat_or = " OR ".join(
                        f"matched_categories @> CAST(:sc_{i} AS jsonb)"
                        for i in range(len(social_cats))
                    )
                    conditions.append(f"({cat_or})")
                    for i, c in enumerate(social_cats):
                        params[f"sc_{i}"] = json.dumps([c])

        # --- area filter condition ---
        area_condition = ""
        if resolved_area_ids:
            area_condition = "area_id = ANY(:area_ids)"
            params["area_ids"] = resolved_area_ids

        # Build WHERE with area filter
        where_with_area = " AND ".join(
            conditions + ([area_condition] if area_condition else [])
        )
        where_no_area = " AND ".join(conditions)

        # --- Query with area filter first ---
        result = _query_trends(conn, where_with_area, params, social_cats)

        # --- Fallback: if area filter yields 0 buzz, retry without it ---
        is_fallback = False
        if area_condition and result["total_buzz"] == 0:
            result = _query_trends(conn, where_no_area, params, social_cats)
            is_fallback = True

    return SocialTrendsResponse(
        total_buzz=result["total_buzz"],
        avg_sentiment=result["avg_sentiment"],
        total_pos=result["total_pos"],
        total_neg=result["total_neg"],
        by_source=result["by_source"],
        top_keywords=result["top_keywords"],
        evidence_snippets=result["evidence_snippets"],
        daily_trend=result["daily_trend"],
        data_asof=datetime.now().strftime("%Y-%m-%d %H:%M"),
        filtered_area=filtered_area,
        filtered_category=filtered_category,
        is_fallback=is_fallback,
    )


def _query_trends(  # noqa: ANN001
    conn,
    where: str,
    params: dict,
    social_cats: list[str] | None = None,
) -> dict:
    """Run the 5 social-trend queries and return aggregated dict.

    Args:
        social_cats: Gemini-tagged category labels to filter evidence snippets.
    """
    stats = conn.execute(
        text(f"""
            SELECT
                coalesce(sum(buzz_volume), 0),
                round(avg(sentiment_score)::numeric, 3),
                coalesce(sum(sentiment_pos), 0),
                coalesce(sum(sentiment_neg), 0)
            FROM fact_social_trend_daily
            WHERE {where}
        """),
        params,
    ).fetchone()

    sources = conn.execute(
        text(f"""
            SELECT source, count(*), coalesce(sum(buzz_volume), 0)
            FROM fact_social_trend_daily
            WHERE {where}
            GROUP BY source ORDER BY sum(buzz_volume) DESC
        """),
        params,
    ).fetchall()

    kw_rows = conn.execute(
        text(f"""
            SELECT top_keywords
            FROM fact_social_trend_daily
            WHERE {where} AND top_keywords IS NOT NULL
            ORDER BY collected_date DESC LIMIT 50
        """),
        params,
    ).fetchall()

    # 에비던스: 카테고리 필터 시 넓게 수집 후 스니펫별 필터
    ev_limit = 30 if social_cats else 10
    ev_rows = conn.execute(
        text(f"""
            SELECT source, keyword, collected_date, evidence_snippets
            FROM fact_social_trend_daily
            WHERE {where} AND evidence_snippets IS NOT NULL
            ORDER BY collected_date DESC LIMIT {ev_limit}
        """),
        params,
    ).fetchall()

    trend_rows = conn.execute(
        text(f"""
            SELECT collected_date, sum(buzz_volume)
            FROM fact_social_trend_daily
            WHERE {where}
            GROUP BY collected_date ORDER BY collected_date
        """),
        params,
    ).fetchall()

    # Aggregate keywords
    keyword_freq: dict[str, int] = {}
    for row in kw_rows:
        if row[0]:
            kws = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            for kw in kws:
                keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
    top_keywords = [
        kw for kw, _ in sorted(keyword_freq.items(), key=lambda x: -x[1])[:15]
    ]

    # Collect evidence — filter by Gemini-tagged categories per snippet
    evidence: list[EvidenceSnippet] = []
    for row in ev_rows:
        snippets = row[3]
        if snippets:
            parsed = json.loads(snippets) if isinstance(snippets, str) else snippets
            for s in parsed[:5]:
                # 카테고리 필터: 스니펫의 categories 필드가 social_cats와 겹치는지
                if social_cats:
                    snippet_cats = s.get("categories", [])
                    if snippet_cats and not any(
                        c in snippet_cats for c in social_cats
                    ):
                        continue
                evidence.append(EvidenceSnippet(
                    title=s.get("title", ""),
                    url=s.get("url", ""),
                    published_at=s.get("published_at", ""),
                    snippet=s.get("snippet", ""),
                    source=row[0],
                    keyword=row[1],
                ))
        if not social_cats and len(evidence) >= 10:
            break

    # URL 중복 제거
    seen_urls: set[str] = set()
    deduped: list[EvidenceSnippet] = []
    for ev in evidence:
        if ev.url and ev.url in seen_urls:
            continue
        seen_urls.add(ev.url)
        deduped.append(ev)
    evidence = deduped[:10]

    return {
        "total_buzz": int(stats[0]) if stats else 0,
        "avg_sentiment": float(stats[1]) if stats and stats[1] else None,
        "total_pos": int(stats[2]) if stats else 0,
        "total_neg": int(stats[3]) if stats else 0,
        "by_source": [
            SourceBreakdown(source=r[0], count=r[1], buzz=int(r[2]))
            for r in sources
        ],
        "top_keywords": top_keywords,
        "evidence_snippets": evidence[:10],
        "daily_trend": [
            TrendDayPoint(date=str(r[0]), buzz=int(r[1]))
            for r in trend_rows
        ],
    }
