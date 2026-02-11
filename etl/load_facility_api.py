"""Load D8 (집객시설-상권) via Seoul Open API → fact_facility_area_qtr.

Source: VwsmTrdarFcltyQq (OA-15580)
Format: narrow/EAV — one row per (area_id, qtr, facility_type)

Note: This API ignores quarter parameter and returns ALL quarters in a single
      response (31K+ rows). We fetch once and use STDR_YYQU_CD from each row.

Usage:
    docker compose run --rm --entrypoint python etl -m etl.load_facility_api
"""

from __future__ import annotations

from typing import Any

from etl.collectors.seoul_api_collector import SeoulAPICollector, API_SERVICES
from etl.db import execute_sql

# API 컬럼 → facility_type 매핑
FACILITY_COLUMNS: dict[str, str] = {
    "VIATR_FCLTY_CO": "VIATR_FCLTY",    # 관광시설
    "PBLOFC_CO": "PBLOFC",              # 관공서
    "BANK_CO": "BANK",                  # 은행
    "GEHSPT_CO": "GEHSPT",              # 종합병원(대형)
    "GNRL_HSPTL_CO": "GNRL_HSPTL",      # 일반병원
    "PARMACY_CO": "PARMACY",            # 약국
    "KNDRGR_CO": "KNDRGR",              # 유치원
    "ELESCH_CO": "ELESCH",              # 초등학교
    "MSKUL_CO": "MSKUL",                # 중학교
    "HGSCHL_CO": "HGSCHL",              # 고등학교
    "UNIV_CO": "UNIV",                  # 대학교
    "DRTS_CO": "DRTS",                  # 백화점
    "SUPMK_CO": "SUPMK",                # 대형마트
    "THEAT_CO": "THEAT",                # 극장
    "STAYNG_FCLTY_CO": "STAYNG_FCLTY",  # 숙박시설
    "ARPRT_CO": "ARPRT",                # 공항
    "RLROAD_STATN_CO": "RLROAD_STATN",  # 철도역
    "BUS_TRMINL_CO": "BUS_TRMINL",      # 버스터미널
    "SUBWAY_STATN_CO": "SUBWAY_STATN",  # 지하철역
    "BUS_STTN_CO": "BUS_STTN",          # 버스정류장
}

# 한글 라벨 (검증 출력용)
FACILITY_LABELS: dict[str, str] = {
    "VIATR_FCLTY": "관광시설",
    "PBLOFC": "관공서",
    "BANK": "은행",
    "GEHSPT": "종합병원(대형)",
    "GNRL_HSPTL": "일반병원",
    "PARMACY": "약국",
    "KNDRGR": "유치원",
    "ELESCH": "초등학교",
    "MSKUL": "중학교",
    "HGSCHL": "고등학교",
    "UNIV": "대학교",
    "DRTS": "백화점",
    "SUPMK": "대형마트",
    "THEAT": "극장",
    "STAYNG_FCLTY": "숙박시설",
    "ARPRT": "공항",
    "RLROAD_STATN": "철도역",
    "BUS_TRMINL": "버스터미널",
    "SUBWAY_STATN": "지하철역",
    "BUS_STTN": "버스정류장",
}


def get_seongsu_trdar_mapping() -> dict[str, int]:
    """Get commercial area code to area_id mapping for Seongsu-dong."""
    result = execute_sql(
        "SELECT area_code, area_id FROM dim_area WHERE area_type = 'COMMERCIAL_AREA'"
    )
    return {str(row[0]): row[1] for row in result}


def upsert_facility(
    rows: list[dict[str, Any]],
    area_mapping: dict[str, int],
) -> int:
    """Upsert facility data to fact_facility_area_qtr (narrow format).

    Uses STDR_YYQU_CD from each row as the actual quarter.
    """
    upserted = 0

    for row in rows:
        trdar_cd = str(row.get("TRDAR_CD", ""))
        area_id = area_mapping.get(trdar_cd)
        if area_id is None:
            continue

        qtr = str(row.get("STDR_YYQU_CD", ""))
        if not qtr:
            continue

        for api_col, facility_type in FACILITY_COLUMNS.items():
            raw_val = row.get(api_col)
            if raw_val is None:
                continue
            cnt = int(float(raw_val))

            execute_sql(
                """
                INSERT INTO fact_facility_area_qtr (area_id, qtr, facility_type, facility_cnt)
                VALUES (:area_id, :qtr, :facility_type, :facility_cnt)
                ON CONFLICT (area_id, qtr, facility_type) DO UPDATE SET
                    facility_cnt = EXCLUDED.facility_cnt
                """,
                {
                    "area_id": area_id,
                    "qtr": qtr,
                    "facility_type": facility_type,
                    "facility_cnt": cnt,
                },
            )
            upserted += 1

    return upserted


def main() -> None:
    print("=" * 60)
    print("Load D8 (집객시설-상권) via API → fact_facility_area_qtr")
    print("=" * 60)

    area_mapping = get_seongsu_trdar_mapping()
    if not area_mapping:
        print("\n[ERROR] No commercial areas in dim_area. Run load_boundaries first.")
        return
    print(f"\n[Step 1] Seongsu commercial area mapping: {len(area_mapping)} areas")

    collector = SeoulAPICollector()
    service = API_SERVICES["D8_FACILITY"]

    # This API returns ALL quarters in a single response (~31K rows)
    print(f"\n[Step 2] Fetching all data from Seoul API ({service})...")
    try:
        all_rows = collector.fetch_all(service)
        print(f"  Total rows fetched: {len(all_rows):,}")
    except Exception as e:
        print(f"  [ERROR] Failed to fetch: {e}")
        return

    # Filter Seongsu rows
    seongsu_rows = [r for r in all_rows if str(r.get("TRDAR_CD", "")) in area_mapping]
    print(f"  Seongsu rows: {len(seongsu_rows):,}")

    # Show distinct quarters available
    distinct_qtrs = sorted(set(str(r.get("STDR_YYQU_CD", "")) for r in seongsu_rows))
    print(f"  Quarters in data: {distinct_qtrs}")

    if not seongsu_rows:
        print("  [ERROR] No Seongsu data found")
        return

    # Clear existing data and reload
    print(f"\n[Step 3] Upserting facility data...")
    upserted = upsert_facility(seongsu_rows, area_mapping)
    print(f"  Upserted: {upserted:,} rows")

    # ================================================================
    # Verification
    # ================================================================
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    result = execute_sql("SELECT count(*) FROM fact_facility_area_qtr")
    total_rows = list(result)[0][0]
    print(f"\n  Total rows in fact_facility_area_qtr: {total_rows:,}")

    result = execute_sql("""
        SELECT qtr, count(DISTINCT area_id) as areas, count(*) as rows
        FROM fact_facility_area_qtr
        GROUP BY qtr
        ORDER BY qtr DESC
    """)
    print("\n  Quarters coverage:")
    for row in result:
        print(f"    {row[0]}: {row[1]} areas, {row[2]} facility entries")

    result = execute_sql("""
        SELECT facility_type, sum(facility_cnt) as total
        FROM fact_facility_area_qtr
        GROUP BY facility_type
        ORDER BY total DESC
        LIMIT 10
    """)
    print("\n  Top 10 facility types (all quarters):")
    for row in result:
        label = FACILITY_LABELS.get(row[0], row[0])
        print(f"    {row[0]:20s} ({label}): {row[1]:,}")

    print(f"\n✓ Done! Total upserted: {upserted:,}")


if __name__ == "__main__":
    main()
