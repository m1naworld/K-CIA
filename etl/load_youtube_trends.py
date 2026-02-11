"""Load YouTube trend data → fact_social_trend_daily.

Searches YouTube for Seongsu-dong related keywords, aggregates by date,
and performs best-effort area_id mapping from video titles/descriptions.

Usage:
    docker compose run --rm --entrypoint python etl -m etl.load_youtube_trends
    # or
    python -m etl.load_youtube_trends
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from etl.category_tagger import tag_snippets_batch
from etl.collectors.youtube_collector import YouTubeCollector
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


def get_default_keywords() -> list[str]:
    """Get default search keywords from social_module_config."""
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
    """Get collection window from config."""
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
    """Build keyword → area_id mapping from dim_area commercial areas.

    Returns:
        Dict mapping area name keywords to area_id.
        e.g., {"서울숲": 42, "뚝섬": 43, "성수역": 44, ...}
    """
    # 너무 일반적인 프래그먼트 — 성수동 전체 콘텐츠에 등장하므로 매핑 제외
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
        # real_name 매핑 추가 (e.g., "수제화거리", "뚝섬 카페거리")
        if real_name:
            mapping[real_name] = area_id
            for part in re.split(r"[·\s/()]", real_name):
                cleaned = part.strip()
                if len(cleaned) >= 2 and cleaned not in GENERIC_FRAGMENTS:
                    mapping[cleaned] = area_id

    # 랜드마크 수동 매핑 (카페거리는 2개 → 구체 명칭만 등록)
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
    title: str,
    description: str,
    area_mapping: dict[str, int],
) -> list[int]:
    """Match ALL area_ids from video title/description.

    Returns deduplicated list of area_ids (longer keywords matched first).
    A video mentioning both "연무장길" and "서울숲" maps to both areas.
    """
    text = f"{title} {description}"
    seen: set[int] = set()
    result: list[int] = []
    for keyword in sorted(area_mapping, key=len, reverse=True):
        if keyword in text:
            aid = area_mapping[keyword]
            if aid not in seen:
                seen.add(aid)
                result.append(aid)
    return result


def extract_hashtags(text: str) -> str:
    """Extract hashtags and return a space-joined string without '#'."""
    tags = re.findall(r"#([0-9A-Za-z가-힣_]+)", text)
    if not tags:
        return ""
    seen: set[str] = set()
    ordered = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            ordered.append(tag)
    return " ".join(ordered)


def simple_sentiment(title: str, description: str) -> tuple[float | None, int, int]:
    """Simple keyword-based sentiment scoring.

    Returns:
        (sentiment_score, pos_count, neg_count)
        sentiment_score: -1.0 ~ 1.0, None if no signal
    """
    text = f"{title} {description}".lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    total = pos + neg
    if total == 0:
        return None, 0, 0
    score = round((pos - neg) / total, 3)
    return score, pos, neg


# 상권 분석과 무관한 콘텐츠 제외 패턴 (소문자 비교)
EXCLUDE_PATTERNS = [
    "playlist", "play list", "플리", "플레이리스트",
    "노동요", "bgm", "asmr", "모음곡",
    "원룸텔", "레지던스", "전세", "월세", "매매", "분양", "부동산",
    "평택", "군자역", "건대", "강남", "홍대", "이태원", "잠실",
]
# 성수동 언급 필수 확인용
SEONGSU_MARKERS = ["성수", "뚝섬", "서울숲"]


def is_relevant(title: str, desc: str) -> bool:
    """Check if content is relevant to Seongsu-dong commercial area analysis."""
    text = f"{title} {desc}".lower()
    # 제외 패턴 매칭
    if any(pat in text for pat in EXCLUDE_PATTERNS):
        return False
    # 성수동 관련 키워드가 하나라도 있어야 함
    if not any(m in text for m in SEONGSU_MARKERS):
        return False
    return True


def enrich_videos(
    collector: YouTubeCollector,
    videos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Replace truncated descriptions with full ones via videos.list.

    Also adds 'tags' field from creator-set video tags.
    Cost: 1 API unit per 50 videos.
    """
    video_ids = [v["video_id"] for v in videos if v.get("video_id")]
    if not video_ids:
        return videos

    try:
        details = collector.get_video_details(video_ids)
    except Exception as e:
        print(f"  [WARN] videos.list failed, using truncated descriptions: {e}")
        return videos

    enriched = 0
    for video in videos:
        vid = video.get("video_id", "")
        if vid in details:
            video["description"] = details[vid]["description"]
            video["tags"] = details[vid].get("tags", [])
            enriched += 1

    print(f"  Enriched {enriched}/{len(videos)} videos with full descriptions")
    return videos


def aggregate_by_date_area(
    videos: list[dict[str, Any]],
    keyword: str,
    area_mapping: dict[str, int],
    place_resolver=None,
) -> dict[tuple[str, int | None], dict[str, Any]]:
    """Aggregate videos by (date, area_id).

    Each video maps to one or more area_ids → separate rows per area.
    Videos with no area match get area_id=None (성수동 전체).

    Returns:
        Dict[(date_str, area_id|None), {buzz_volume, sentiment_*, snippets, ...}]
    """
    skipped = 0
    prepared: list[dict[str, Any]] = []
    for video in videos:
        title = video.get("title", "")
        desc = video.get("description", "")

        if not is_relevant(title, desc):
            skipped += 1
            continue

        pub_str = video.get("published_at", "")
        try:
            pub_date = datetime.fromisoformat(
                pub_str.replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            continue

        hashtags = extract_hashtags(f"{title} {desc}")
        video_tags = video.get("tags", [])
        tags_text = " ".join(video_tags) if video_tags else ""
        match_text = f"{title} {desc} {hashtags} {tags_text}".strip()

        prepared.append({
            "title": title,
            "desc": desc,
            "hashtags": hashtags,
            "tags_text": tags_text,
            "match_text": match_text,
            "pub_str": pub_str,
            "pub_date": pub_date,
            "video_id": video.get("video_id", ""),
            "area_ids": [],  # filled below
        })

    # ── Phase 1 (primary): Spatial resolution — address/place → geocode → ST_Intersects
    geo_mapped = 0
    if place_resolver:
        all_snippets = [
            {
                "title": p["title"],
                "snippet": f"{p['desc']} {p['hashtags']} {p['tags_text']}".strip(),
            }
            for p in prepared
        ]
        resolved_multi = place_resolver.resolve_area_ids_multi(all_snippets)
        for p, aids in zip(prepared, resolved_multi):
            if aids:
                p["area_ids"] = aids
                geo_mapped += 1

    # ── Phase 2 (fallback): Keyword matching for videos not spatially resolved
    kw_mapped = 0
    for p in prepared:
        if not p["area_ids"]:
            match_text = p["match_text"]
            aids = match_area_ids(p["title"], match_text, area_mapping)
            if aids:
                p["area_ids"] = aids
                kw_mapped += 1

    # Aggregate by (date, area_id)
    BucketKey = tuple[str, int | None]
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
            "url": f"https://www.youtube.com/watch?v={item['video_id']}",
            "published_at": item["pub_str"],
            "snippet": f"{item['desc']} {item['hashtags']}"[:300].strip(),
        }
        score, pos, neg = simple_sentiment(item["title"], item["desc"])
        words = re.findall(
            r"[가-힣]{2,}",
            f"{item['title']} {item['desc']} {item['hashtags']} {item['tags_text']}",
        )

        # Distribute to each matched area + always also to None (전체)
        targets: list[int | None] = list(item["area_ids"]) if item["area_ids"] else []
        targets.append(None)  # 모든 영상은 area_id=None (전체)에도 집계

        for aid in targets:
            key: BucketKey = (item["pub_date"], aid)
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


BucketKey = tuple[str, int | None]


def tag_daily_snippets(
    daily_data: dict[BucketKey, dict[str, Any]],
) -> None:
    """Tag evidence snippets with Gemini Flash and write matched_categories back.

    Deduplicates snippets by URL before tagging to save Gemini calls,
    then distributes tags back to all buckets sharing the same snippet.
    """
    # Deduplicate snippets by URL for efficient tagging
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

    print(f"  Gemini tagging {len(unique_snippets)} unique snippets...")
    tags = tag_snippets_batch(unique_snippets)

    # Map URL → categories
    url_to_cats: dict[str, list[str]] = {}
    for snippet, cats in zip(unique_snippets, tags):
        url_to_cats[snippet.get("url", "")] = cats

    # Distribute tags back to all buckets
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
    print(f"  Category-tagged buckets: {tagged}/{len(daily_data)}")


def upsert_trends(
    keyword: str,
    daily_data: dict[BucketKey, dict[str, Any]],
) -> int:
    """Upsert trend data keyed by (date, area_id) to fact_social_trend_daily."""
    upserted = 0
    for (date_str, area_id), data in daily_data.items():
        execute_sql(
            """
            INSERT INTO fact_social_trend_daily
                (area_id, source, collected_date, keyword,
                 buzz_volume, sentiment_score, sentiment_pos, sentiment_neg,
                 top_keywords, evidence_snippets, matched_categories)
            VALUES
                (:area_id, 'youtube', :collected_date, :keyword,
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
    print("Load YouTube Trends → fact_social_trend_daily")
    print("=" * 60)

    # Config
    keywords = get_default_keywords()
    days = get_collection_days()
    print(f"\n[Config] Keywords: {keywords}")
    print(f"[Config] Collection window: {days} days")

    # Area mapping for best-effort matching
    area_mapping = get_area_mapping()
    print(f"[Config] Area mapping entries: {len(area_mapping)}")

    # LLM + Kakao place resolver
    place_resolver = build_place_resolver()
    if place_resolver:
        print("[Config] LLM+Kakao place mapping: enabled")
    else:
        print("[Config] LLM+Kakao place mapping: disabled")

    # YouTube collector
    try:
        collector = YouTubeCollector()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return

    total_upserted = 0
    total_videos = 0

    for i, keyword in enumerate(keywords, 1):
        print(f"\n[{i}/{len(keywords)}] Searching: '{keyword}' (last {days} days)...")

        try:
            videos = collector.search(keyword, days=days, max_results=50)
        except Exception as e:
            print(f"  [ERROR] Search failed: {e}")
            continue

        print(f"  Videos found: {len(videos)}")
        total_videos += len(videos)

        if not videos:
            continue

        # Enrich with full descriptions via videos.list
        videos = enrich_videos(collector, videos)

        # Aggregate by (date, area_id)
        daily_data = aggregate_by_date_area(videos, keyword, area_mapping, place_resolver)
        n_buckets = len(daily_data)
        n_area_mapped = sum(
            1 for (_, aid) in daily_data if aid is not None
        )
        n_dates = len({d for d, _ in daily_data})
        print(f"  Buckets: {n_buckets} ({n_dates} dates × {n_area_mapped} area-mapped + {n_buckets - n_area_mapped} global)")

        # Gemini Flash 업종 태깅
        tag_daily_snippets(daily_data)

        # Upsert
        upserted = upsert_trends(keyword, daily_data)
        total_upserted += upserted
        print(f"  Upserted: {upserted} rows")

    # ================================================================
    # Verification
    # ================================================================
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    result = execute_sql(
        "SELECT count(*) FROM fact_social_trend_daily WHERE source = 'youtube'"
    )
    total_rows = next(iter(result))[0]
    print(f"\n  Total YouTube rows: {total_rows}")

    result = execute_sql("""
        SELECT keyword, count(*) as rows, sum(buzz_volume) as total_buzz
        FROM fact_social_trend_daily
        WHERE source = 'youtube'
        GROUP BY keyword
        ORDER BY total_buzz DESC
    """)
    print("\n  By keyword:")
    for row in result:
        print(f"    {row[0]:20s}: {row[1]} rows, {row[2]} buzz")

    result = execute_sql("""
        SELECT count(*) FROM fact_social_trend_daily
        WHERE source = 'youtube' AND area_id IS NOT NULL
    """)
    mapped_rows = next(iter(result))[0]
    pct = (mapped_rows / total_rows * 100) if total_rows > 0 else 0
    print(f"\n  Area-mapped rows: {mapped_rows}/{total_rows} ({pct:.1f}%)")

    # 상권별 커버리지
    result = execute_sql("""
        SELECT
            da.area_name, da.real_name,
            count(s.trend_id) as rows,
            coalesce(sum(s.buzz_volume), 0) as buzz
        FROM dim_area da
        LEFT JOIN fact_social_trend_daily s
            ON da.area_id = s.area_id AND s.source = 'youtube'
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

    print(f"\n✓ Done! Videos: {total_videos}, Upserted: {total_upserted} rows")


if __name__ == "__main__":
    main()
