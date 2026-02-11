"""Social Agent — queries SNS trend data when social module is enabled."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from db import engine


def _is_social_enabled() -> bool:
    """Check if the social module is enabled via social_module_config."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT config_value FROM social_module_config "
                    "WHERE config_key = 'enabled'"
                )
            )
            row = result.fetchone()
            return row is not None and row[0].lower() == "true"
    except Exception:
        return False


def _fetch_social_trends(
    keyword: str | None = None,
    days: int = 30,
    limit: int = 50,
) -> dict[str, Any]:
    """Fetch recent social trend data from fact_social_trend_daily.

    Returns:
        Dict with keys: items, total_buzz, avg_sentiment, top_keywords,
        by_source, evidence_snippets
    """
    conditions = ["collected_date >= current_date - :days"]
    params: dict[str, Any] = {"days": days, "limit": limit}

    if keyword:
        conditions.append("keyword ILIKE :keyword")
        params["keyword"] = f"%{keyword}%"

    where_clause = " AND ".join(conditions)

    with engine.connect() as conn:
        # Aggregate stats
        stats_sql = f"""
            SELECT
                count(*) AS total_rows,
                coalesce(sum(buzz_volume), 0) AS total_buzz,
                round(avg(sentiment_score)::numeric, 3) AS avg_sentiment,
                sum(sentiment_pos) AS total_pos,
                sum(sentiment_neg) AS total_neg
            FROM fact_social_trend_daily
            WHERE {where_clause}
        """
        stats = conn.execute(text(stats_sql), params).fetchone()

        # By source breakdown
        source_sql = f"""
            SELECT source, count(*) AS cnt, sum(buzz_volume) AS buzz
            FROM fact_social_trend_daily
            WHERE {where_clause}
            GROUP BY source ORDER BY buzz DESC
        """
        sources = conn.execute(text(source_sql), params).fetchall()

        # Top keywords across all entries
        kw_sql = f"""
            SELECT top_keywords
            FROM fact_social_trend_daily
            WHERE {where_clause} AND top_keywords IS NOT NULL
            ORDER BY collected_date DESC
            LIMIT :limit
        """
        kw_rows = conn.execute(text(kw_sql), params).fetchall()

        # Recent evidence snippets
        ev_sql = f"""
            SELECT source, keyword, collected_date, evidence_snippets
            FROM fact_social_trend_daily
            WHERE {where_clause} AND evidence_snippets IS NOT NULL
            ORDER BY collected_date DESC
            LIMIT 10
        """
        ev_rows = conn.execute(text(ev_sql), params).fetchall()

        # Daily buzz trend
        trend_sql = f"""
            SELECT collected_date, sum(buzz_volume) AS buzz
            FROM fact_social_trend_daily
            WHERE {where_clause}
            GROUP BY collected_date
            ORDER BY collected_date
        """
        trend_rows = conn.execute(text(trend_sql), params).fetchall()

    # Aggregate top keywords
    keyword_freq: dict[str, int] = {}
    for row in kw_rows:
        if row[0]:
            kws = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            for kw in kws:
                keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
    top_keywords = [
        kw for kw, _ in sorted(keyword_freq.items(), key=lambda x: -x[1])[:15]
    ]

    # Collect evidence snippets
    evidence: list[dict] = []
    for row in ev_rows:
        snippets = row[3]
        if snippets:
            parsed = json.loads(snippets) if isinstance(snippets, str) else snippets
            for s in parsed[:2]:
                s["source"] = row[0]
                s["keyword"] = row[1]
                evidence.append(s)
        if len(evidence) >= 10:
            break

    return {
        "total_rows": stats[0] if stats else 0,
        "total_buzz": int(stats[1]) if stats else 0,
        "avg_sentiment": float(stats[2]) if stats and stats[2] else None,
        "total_pos": int(stats[3]) if stats else 0,
        "total_neg": int(stats[4]) if stats else 0,
        "by_source": [
            {"source": r[0], "count": r[1], "buzz": int(r[2])} for r in sources
        ],
        "top_keywords": top_keywords,
        "evidence_snippets": evidence[:10],
        "daily_trend": [
            {"date": str(r[0]), "buzz": int(r[1])} for r in trend_rows
        ],
    }


def social_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: fetch social trend data if module is enabled.

    Sets state["social_result"] with trend data, or None if disabled.
    """
    if not _is_social_enabled():
        print("[Social] Module disabled, skipping", flush=True)
        return {"social_result": None}

    question = state.get("question", "")

    # Extract potential keyword from question for focused search
    search_keyword = None
    for term in ["카페", "맛집", "팝업", "브런치", "디저트", "베이커리", "치킨"]:
        if term in question:
            search_keyword = f"성수동 {term}"
            break

    print(f"[Social] Fetching trends (keyword={search_keyword})", flush=True)
    social_data = _fetch_social_trends(keyword=search_keyword, days=30)
    print(
        f"[Social] Found {social_data['total_rows']} rows, "
        f"buzz={social_data['total_buzz']}, "
        f"keywords={social_data['top_keywords'][:5]}",
        flush=True,
    )

    return {"social_result": social_data}
