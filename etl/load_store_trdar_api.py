"""Load D2 (점포-상권) via Seoul Open API → fact_store_area_qtr.

Usage:
    docker compose run --rm --entrypoint python etl -m etl.load_store_trdar_api
    docker compose run --rm --entrypoint python etl -m etl.load_store_trdar_api 20244
"""

from __future__ import annotations

import sys
from typing import Any

from etl.collectors.seoul_api_collector import SeoulAPICollector, API_SERVICES
from etl.db import execute_sql

TARGET_QUARTERS = ["20253", "20252", "20251", "20244", "20243", "20242", "20241"]


def get_seongsu_trdar_mapping() -> dict[str, int]:
    """Get commercial area code to area_id mapping for Seongsu-dong."""
    result = execute_sql(
        "SELECT area_code, area_id FROM dim_area WHERE area_type = 'COMMERCIAL_AREA'"
    )
    return {str(row[0]): row[1] for row in result}


def upsert_dim_category(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Upsert unique service categories to dim_category."""
    seen = set()
    for row in rows:
        code = row.get("SVC_INDUTY_CD")
        name = row.get("SVC_INDUTY_CD_NM")
        if code and name and code not in seen:
            execute_sql(
                """
                INSERT INTO dim_category (service_code, service_name)
                VALUES (:code, :name)
                ON CONFLICT (service_code) DO UPDATE SET service_name = EXCLUDED.service_name
                """,
                {"code": str(code), "name": str(name)},
            )
            seen.add(code)

    result = execute_sql("SELECT service_code, cat_id FROM dim_category")
    return {str(row[0]): row[1] for row in result}


def upsert_fact_store(
    rows: list[dict[str, Any]],
    qtr: str,
    area_mapping: dict[str, int],
    cat_mapping: dict[str, int],
) -> int:
    """Upsert store data to fact_store_area_qtr."""
    upserted = 0

    for row in rows:
        trdar_cd = str(row.get("TRDAR_CD", ""))

        area_id = area_mapping.get(trdar_cd)
        if area_id is None:
            continue

        service_code = str(row.get("SVC_INDUTY_CD", ""))
        cat_id = cat_mapping.get(service_code)
        if cat_id is None:
            continue

        store_cnt = row.get("STOR_CO")
        open_cnt = row.get("OPBIZ_STOR_CO")
        close_cnt = row.get("CLSBIZ_STOR_CO")
        franchise_cnt = row.get("FRC_STOR_CO")

        execute_sql(
            """
            INSERT INTO fact_store_area_qtr (area_id, qtr, cat_id, store_cnt, open_cnt, close_cnt, franchise_cnt)
            VALUES (:area_id, :qtr, :cat_id, :store_cnt, :open_cnt, :close_cnt, :franchise_cnt)
            ON CONFLICT (area_id, qtr, cat_id) DO UPDATE SET
                store_cnt = EXCLUDED.store_cnt,
                open_cnt = EXCLUDED.open_cnt,
                close_cnt = EXCLUDED.close_cnt,
                franchise_cnt = EXCLUDED.franchise_cnt
            """,
            {
                "area_id": area_id,
                "qtr": qtr,
                "cat_id": cat_id,
                "store_cnt": int(store_cnt) if store_cnt else None,
                "open_cnt": int(open_cnt) if open_cnt else None,
                "close_cnt": int(close_cnt) if close_cnt else None,
                "franchise_cnt": int(franchise_cnt) if franchise_cnt else None,
            },
        )
        upserted += 1

    return upserted


def main() -> None:
    print("=" * 60)
    print("Load D2 (점포-상권) via API → fact_store_area_qtr")
    print("=" * 60)

    quarters = TARGET_QUARTERS
    if len(sys.argv) > 1:
        quarters = sys.argv[1:]
        print(f"[INFO] Using custom quarters: {quarters}")

    area_mapping = get_seongsu_trdar_mapping()
    if not area_mapping:
        print("\n[ERROR] No commercial areas in dim_area. Run load_boundaries first.")
        sys.exit(1)
    print(f"\n[Step 1] Seongsu commercial area mapping: {len(area_mapping)} areas")
    print(f"  Codes: {list(area_mapping.keys())[:5]}...")

    collector = SeoulAPICollector()
    service = API_SERVICES["D2_STORE_TRDAR"]

    total_upserted = 0
    cat_mapping: dict[str, int] = {}

    for qtr in quarters:
        print(f"\n[Step 2] Fetching quarter {qtr} from Seoul API...")

        try:
            rows = collector.fetch_all(service, extra_params=[qtr])
            print(f"  Total rows fetched: {len(rows):,}")
        except Exception as e:
            print(f"  [ERROR] Failed to fetch: {e}")
            continue

        if not rows:
            print(f"  [INFO] No data for quarter {qtr}")
            continue

        seongsu_rows = [r for r in rows if str(r.get("TRDAR_CD", "")) in area_mapping]
        print(f"  Seongsu rows: {len(seongsu_rows):,}")

        if not seongsu_rows:
            sample_codes = list({str(r.get("TRDAR_CD", "")) for r in rows[:20]})
            print(f"  [DEBUG] Sample TRDAR codes from API: {sample_codes[:5]}")
            continue

        cat_mapping.update(upsert_dim_category(seongsu_rows))
        upserted = upsert_fact_store(seongsu_rows, qtr, area_mapping, cat_mapping)
        print(f"  Upserted: {upserted:,}")
        total_upserted += upserted

    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    # 상권별 점포 데이터 확인
    result = execute_sql("""
        SELECT da.area_type, COUNT(*) as rows
        FROM fact_store_area_qtr fs
        JOIN dim_area da ON da.area_id = fs.area_id
        GROUP BY da.area_type
    """)
    print("\n  Store data by area_type:")
    for row in result:
        print(f"    {row[0]}: {row[1]:,} rows")

    result = execute_sql(
        """
        SELECT qtr, count(*) as cnt
        FROM fact_store_area_qtr fs
        JOIN dim_area da ON da.area_id = fs.area_id
        WHERE da.area_type = 'COMMERCIAL_AREA'
        GROUP BY qtr
        ORDER BY qtr DESC
        LIMIT 8
        """
    )
    print("\n  Commercial area quarters coverage:")
    for row in result:
        print(f"    {row[0]}: {row[1]} rows")

    if total_upserted > 0:
        print(f"\n✓ Done! Total upserted: {total_upserted:,}")
    else:
        print("\n✗ Warning: No data loaded")


if __name__ == "__main__":
    main()
