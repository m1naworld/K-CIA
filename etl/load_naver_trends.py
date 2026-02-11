"""Load Naver Blog/Cafe trend data → fact_social_trend_daily.

Searches Naver Blog and Cafe for Seongsu-dong related keywords,
aggregates by (date, area_id), and performs spatial area_id mapping.

Usage:
    python -m etl.load_naver_trends
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from etl.category_tagger import tag_snippets_batch
from etl.collectors.naver_collector import NaverCollector
from etl.db import execute_sql
from etl.place_mapper import build_place_resolver

# ── 감성 분석용 키워드 (간이) ─────────────────────────────────
POSITIVE_WORDS = [
    "맛집", "추천", "핫플", "인기", "좋은", "최고", "대박", "사랑",
    "예쁜", "멋진", "분위기", "감성", "힐링", "만족", "성공",
    "오픈", "신상", "인스타", "핫한", "트렌디",
]
NEGATIVE_WORDS = [
    "폐업", "망한", "실패", "실망", "별로", "최악", "비싼", "줄었",
    "위기", "문닫", "안좋", "후회", "노맛", "비추", "사기",
]


def _strip_html(text: str) -> str:
    """Remove HTML tags from Naver API response."""
    return re.sub(r"<[^>]+>", "", text)


def get_default_keywords() -> list[str]:
    try:
        result = execute_sql(
            "SELECT config_value FROM social_module_config "
            "WHERE config_key = 'default_keywords'"
        )
        row = next(iter(result), None)
        if row:
            return json.loads(row[0])
    except Exception:
        pass
    return ["성수동 카페", "성수동 맛집", "성수동 팝업", "성수 브런치", "성수 디저트"]


def get_collection_days() -> int:
    try:
        result = execute_sql(
            "SELECT config_value FROM social_module_config "
            "WHERE config_key = 'collection_days'"
        )
        row = next(iter(result), None)
        if row:
            return int(row[0])
    except Exception:
        pass
    return 30


def get_area_mapping() -> dict[str, int]:
    """Build keyword → area_id mapping from dim_area commercial areas."""
    GENERIC_FRAGMENTS = {"성수", "성수동", "서울", "카페", "맛집", "상가", "골목", "팝업"}

    result = execute_sql(
        "SELECT area_id, area_name, real_name FROM dim_area "
        "WHERE area_type = 'COMMERCIAL_AREA'"
    )
    mapping: dict[str, int] = {}
    for area_id, area_name, real_name in result:
        mapping[area_name] = area_id
        for part in re.split(r"[·\s/()]", area_name):
            cleaned = part.strip()
            if len(cleaned) >= 2 and cleaned not in GENERIC_FRAGMENTS:
                mapping[cleaned] = area_id
        if real_name:
            mapping[real_name] = area_id
            for part in re.split(r"[·\s/()]", real_name):
                cleaned = part.strip()
                if len(cleaned) >= 2 and cleaned not in GENERIC_FRAGMENTS:
                    mapping[cleaned] = area_id

    LANDMARKS = {
        "연무장길": 14,
        "연무장길 카페거리": 14,
        "대림창고": 15,
        "서울숲": 19,
        "헤이그라운드": 13,
        "성수IT": 12,
        "성수IT밸리": 12,
        "성수IT벨리": 12,
    }
    for name, aid in LANDMARKS.items():
        if name not in mapping:
            mapping[name] = aid

    return mapping


def match_area_ids(
    title: str, description: str, area_mapping: dict[str, int],
) -> list[int]:
    """Match ALL area_ids from text (longer keywords first, deduplicated)."""
    text = f"{title} {description}"
    seen: set[int] = set()
    result: list[int] = []
    for kw in sorted(area_mapping, key=len, reverse=True):
        if kw in text:
            aid = area_mapping[kw]
            if aid not in seen:
                seen.add(aid)
                result.append(aid)
    return result


def simple_sentiment(title: str, desc: str) -> tuple[float | None, int, int]:
    text = f"{title} {desc}".lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    total = pos + neg
    if total == 0:
        return None, 0, 0
    return round((pos - neg) / total, 3), pos, neg


def _parse_blog_date(postdate: str) -> str | None:
    """Parse Naver blog postdate (YYYYMMDD) → YYYY-MM-DD."""
    try:
        return datetime.strptime(postdate, "%Y%m%d").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


EXCLUDE_PATTERNS = [
    "playlist", "play list", "플리", "플레이리스트",
    "노동요", "bgm", "asmr", "모음곡",
    "원룸텔", "레지던스", "전세", "월세", "매매", "분양", "부동산",
    "평택", "군자역", "건대", "강남", "홍대", "이태원", "잠실",
]
SEONGSU_MARKERS = ["성수", "뚝섬", "서울숲"]


def is_relevant(title: str, desc: str) -> bool:
    text = f"{title} {desc}".lower()
    if any(pat in text for pat in EXCLUDE_PATTERNS):
        return False
    if not any(m in text for m in SEONGSU_MARKERS):
        return False
    return True


BucketKey = tuple[str, int | None]


def aggregate_items(
    items: list[dict[str, Any]],
    source: str,
    keyword: str,
    area_mapping: dict[str, int],
    place_resolver=None,
) -> dict[BucketKey, dict[str, Any]]:
    """Aggregate blog/cafe items by (date, area_id).

    Each item maps to one or more area_ids → separate rows per area.
    Items with no area match get area_id=None (성수동 전체).
    """
    skipped = 0
    prepared: list[dict[str, Any]] = []
    for item in items:
        title = _strip_html(item.get("title", ""))
        desc = _strip_html(item.get("description", ""))

        if not is_relevant(title, desc):
            skipped += 1
            continue

        link = item.get("link", "")

        if source == "naver_blog":
            date_str = _parse_blog_date(item.get("postdate", ""))
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        if not date_str:
            continue

        prepared.append({
            "title": title,
            "desc": desc,
            "link": link,
            "date_str": date_str,
            "area_ids": [],  # filled below
        })

    # ── Phase 1 (primary): Spatial resolution — place/address → geocode → ST_Intersects
    geo_mapped = 0
    if place_resolver:
        all_snippets = [
            {"title": p["title"], "snippet": p["desc"]}
            for p in prepared
        ]
        resolved_multi = place_resolver.resolve_area_ids_multi(all_snippets)
        for p, aids in zip(prepared, resolved_multi):
            if aids:
                p["area_ids"] = aids
                geo_mapped += 1

    # ── Phase 2 (fallback): Keyword matching for items not spatially resolved
    kw_mapped = 0
    for p in prepared:
        if not p["area_ids"]:
            aids = match_area_ids(p["title"], p["desc"], area_mapping)
            if aids:
                p["area_ids"] = aids
                kw_mapped += 1

    # ── Aggregate by (date, area_id)
    buckets: dict[BucketKey, dict[str, Any]] = defaultdict(lambda: {
        "buzz_volume": 0,
        "sentiment_scores": [],
        "sentiment_pos": 0,
        "sentiment_neg": 0,
        "snippets": [],
        "all_words": [],
    })

    for item in prepared:
        snippet_obj = {
            "title": item["title"][:200],
            "url": item["link"],
            "published_at": item["date_str"],
            "snippet": item["desc"][:300],
        }
        score, pos, neg = simple_sentiment(item["title"], item["desc"])
        words = re.findall(r"[가-힣]{2,}", f"{item['title']} {item['desc']}")

        targets: list[int | None] = list(item["area_ids"]) if item["area_ids"] else []
        targets.append(None)  # 모든 아이템은 area_id=None (전체)에도 집계

        for aid in targets:
            key: BucketKey = (item["date_str"], aid)
            bucket = buckets[key]
            bucket["buzz_volume"] += 1
            if score is not None:
                bucket["sentiment_scores"].append(score)
            bucket["sentiment_pos"] += pos
            bucket["sentiment_neg"] += neg
            bucket["snippets"].append(snippet_obj)
            bucket["all_words"].extend(words)

    # Finalize
    result: dict[BucketKey, dict[str, Any]] = {}
    for (date_str, area_id), bucket in buckets.items():
        scores = bucket["sentiment_scores"]
        avg_sentiment = (
            round(sum(scores) / len(scores), 3) if scores else None
        )
        word_freq: dict[str, int] = defaultdict(int)
        for w in bucket["all_words"]:
            if w not in keyword and len(w) >= 2:
                word_freq[w] += 1
        top_kw = [
            w for w, _ in sorted(word_freq.items(), key=lambda x: -x[1])[:10]
        ]

        result[(date_str, area_id)] = {
            "buzz_volume": bucket["buzz_volume"],
            "sentiment_score": avg_sentiment,
            "sentiment_pos": bucket["sentiment_pos"],
            "sentiment_neg": bucket["sentiment_neg"],
            "area_id": area_id,
            "top_keywords": top_kw,
            "evidence_snippets": bucket["snippets"][:5],
        }

    if skipped:
        print(f"    Filtered out: {skipped} irrelevant items")
    total = len(prepared)
    print(f"    Mapping: {geo_mapped}/{total} spatial, {kw_mapped}/{total} keyword-fallback, {total - geo_mapped - kw_mapped}/{total} unmapped")

    return result


def tag_daily_snippets(
    daily_data: dict[BucketKey, dict[str, Any]],
) -> None:
    """Tag evidence snippets with Gemini Flash (deduplicated by URL)."""
    url_to_snippet: dict[str, dict[str, Any]] = {}
    url_to_keys: dict[str, list[tuple[BucketKey, int]]] = defaultdict(list)

    for key, data in daily_data.items():
        for idx, s in enumerate(data["evidence_snippets"]):
            url = s.get("url", "")
            if url and url not in url_to_snippet:
                url_to_snippet[url] = s
            url_to_keys[url].append((key, idx))

    unique_snippets = list(url_to_snippet.values())
    if not unique_snippets:
        return

    print(f"    Gemini tagging {len(unique_snippets)} unique snippets...")
    tags = tag_snippets_batch(unique_snippets)

    url_to_cats: dict[str, list[str]] = {}
    for snippet, cats in zip(unique_snippets, tags):
        url_to_cats[snippet.get("url", "")] = cats

    for url, locations in url_to_keys.items():
        cats = url_to_cats.get(url, [])
        for key, idx in locations:
            if idx < len(daily_data[key]["evidence_snippets"]):
                daily_data[key]["evidence_snippets"][idx]["categories"] = cats
            daily_data[key].setdefault("matched_categories_set", set())
            daily_data[key]["matched_categories_set"].update(cats)

    for data in daily_data.values():
        cat_set = data.pop("matched_categories_set", set())
        data["matched_categories"] = sorted(cat_set)

    tagged = sum(1 for d in daily_data.values() if d["matched_categories"])
    print(f"    Category-tagged buckets: {tagged}/{len(daily_data)}")


def upsert_trends(
    keyword: str,
    source: str,
    daily_data: dict[BucketKey, dict[str, Any]],
) -> int:
    """Upsert trend data keyed by (date, area_id)."""
    upserted = 0
    for (date_str, area_id), data in daily_data.items():
        execute_sql(
            """
            INSERT INTO fact_social_trend_daily
                (area_id, source, collected_date, keyword,
                 buzz_volume, sentiment_score, sentiment_pos, sentiment_neg,
                 top_keywords, evidence_snippets, matched_categories)
            VALUES
                (:area_id, :source, :collected_date, :keyword,
                 :buzz_volume, :sentiment_score, :sentiment_pos, :sentiment_neg,
                 :top_keywords, :evidence_snippets, :matched_categories)
            ON CONFLICT (area_id, source, collected_date, keyword)
            DO UPDATE SET
                buzz_volume = EXCLUDED.buzz_volume,
                sentiment_score = EXCLUDED.sentiment_score,
                sentiment_pos = EXCLUDED.sentiment_pos,
                sentiment_neg = EXCLUDED.sentiment_neg,
                top_keywords = EXCLUDED.top_keywords,
                evidence_snippets = EXCLUDED.evidence_snippets,
                matched_categories = EXCLUDED.matched_categories,
                created_at = now()
            """,
            {
                "area_id": area_id,
                "source": source,
                "collected_date": date_str,
                "keyword": keyword,
                "buzz_volume": data["buzz_volume"],
                "sentiment_score": data["sentiment_score"],
                "sentiment_pos": data["sentiment_pos"],
                "sentiment_neg": data["sentiment_neg"],
                "top_keywords": json.dumps(data["top_keywords"], ensure_ascii=False),
                "evidence_snippets": json.dumps(
                    data["evidence_snippets"], ensure_ascii=False
                ),
                "matched_categories": json.dumps(
                    data.get("matched_categories", []), ensure_ascii=False
                ),
            },
        )
        upserted += 1
    return upserted


def main() -> None:
    print("=" * 60)
    print("Load Naver Blog/Cafe Trends → fact_social_trend_daily")
    print("=" * 60)

    keywords = get_default_keywords()
    days = get_collection_days()
    print(f"\n[Config] Keywords: {keywords}")
    print(f"[Config] Collection window: {days} days")

    area_mapping = get_area_mapping()
    print(f"[Config] Area mapping entries: {len(area_mapping)}")

    place_resolver = build_place_resolver()
    if place_resolver:
        print("[Config] LLM+Kakao place mapping: enabled")
    else:
        print("[Config] LLM+Kakao place mapping: disabled")

    try:
        collector = NaverCollector()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return

    total_upserted = 0
    sources = [
        ("naver_blog", collector.search_blog),
        ("naver_cafe", collector.search_cafe),
    ]

    for source_name, search_fn in sources:
        print(f"\n{'=' * 40}")
        print(f"Source: {source_name}")
        print("=" * 40)

        for i, keyword in enumerate(keywords, 1):
            print(f"\n  [{i}/{len(keywords)}] Searching: '{keyword}'...")

            try:
                items = search_fn(keyword, display=100, sort="date")
            except Exception as e:
                print(f"    [ERROR] Search failed: {e}")
                continue

            print(f"    Items found: {len(items)}")
            if not items:
                continue

            daily_data = aggregate_items(
                items, source_name, keyword, area_mapping, place_resolver
            )
            n_buckets = len(daily_data)
            n_area = sum(1 for (_, aid) in daily_data if aid is not None)
            print(f"    Buckets: {n_buckets} ({n_area} area-mapped + {n_buckets - n_area} global)")

            tag_daily_snippets(daily_data)

            upserted = upsert_trends(keyword, source_name, daily_data)
            total_upserted += upserted
            print(f"    Upserted: {upserted} rows")

    # Verification
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    result = execute_sql(
        "SELECT source, count(*), sum(buzz_volume) "
        "FROM fact_social_trend_daily "
        "WHERE source IN ('naver_blog', 'naver_cafe') "
        "GROUP BY source"
    )
    print("\n  By source:")
    for row in result:
        print(f"    {row[0]:15s}: {row[1]} rows, {row[2]} items")

    result = execute_sql(
        "SELECT count(*) FROM fact_social_trend_daily "
        "WHERE source IN ('naver_blog', 'naver_cafe')"
    )
    total_rows = next(iter(result))[0]

    result = execute_sql("""
        SELECT count(*) FROM fact_social_trend_daily
        WHERE source IN ('naver_blog', 'naver_cafe') AND area_id IS NOT NULL
    """)
    mapped_rows = next(iter(result))[0]
    pct = (mapped_rows / total_rows * 100) if total_rows > 0 else 0
    print(f"\n  Area-mapped: {mapped_rows}/{total_rows} ({pct:.1f}%)")

    # 상권별 커버리지
    result = execute_sql("""
        SELECT
            da.area_name, da.real_name,
            count(s.trend_id) as rows,
            coalesce(sum(s.buzz_volume), 0) as buzz
        FROM dim_area da
        LEFT JOIN fact_social_trend_daily s
            ON da.area_id = s.area_id
            AND s.source IN ('naver_blog', 'naver_cafe')
        WHERE da.area_type = 'COMMERCIAL_AREA'
        GROUP BY da.area_name, da.real_name
        ORDER BY buzz DESC
    """)
    print("\n  Area coverage:")
    covered = 0
    for row in result:
        marker = "✓" if row[2] > 0 else "✗"
        if row[2] > 0:
            covered += 1
        print(f"    {marker} {row[0]:20s} ({row[1]:16s}): {row[2]} rows, {row[3]} buzz")
    total_areas = sum(1 for _ in execute_sql(
        "SELECT 1 FROM dim_area WHERE area_type = 'COMMERCIAL_AREA'"
    ))
    print(f"\n  Area coverage: {covered}/{total_areas} commercial areas")

    print(f"\n✓ Done! Total upserted: {total_upserted} rows")


if __name__ == "__main__":
    main()
