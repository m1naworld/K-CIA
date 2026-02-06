"""Load D1 (추정매출-상권) via Seoul Open API → fact_sales_area_qtr.

Usage:
    docker compose run --rm --entrypoint python etl -m etl.load_sales_api
    docker compose run --rm --entrypoint python etl -m etl.load_sales_api 20244
"""

from __future__ import annotations

import sys
from typing import Any

from etl.collectors.seoul_api_collector import SeoulAPICollector, API_SERVICES
from etl.db import execute_sql

TARGET_QUARTERS = ["20251", "20244", "20243", "20242"]


def get_seongsu_commercial_codes() -> set[str]:
    """Get commercial area codes from dim_area for Seongsu-dong."""
    result = execute_sql(
        "SELECT area_code FROM dim_area WHERE area_type = 'COMMERCIAL_AREA'"
    )
    return {str(row[0]) for row in result}


def get_area_id_mapping() -> dict[str, int]:
    """Get commercial area code to area_id mapping."""
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


def upsert_fact_sales(
    rows: list[dict[str, Any]],
    qtr: str,
    commercial_codes: set[str],
    area_mapping: dict[str, int],
    cat_mapping: dict[str, int],
) -> int:
    """Upsert sales data to fact_sales_area_qtr."""
    upserted = 0
    
    for row in rows:
        commercial_code = str(row.get("TRDAR_CD", ""))
        
        if commercial_code not in commercial_codes:
            continue
        
        area_id = area_mapping.get(commercial_code)
        if area_id is None:
            continue
        
        service_code = str(row.get("SVC_INDUTY_CD", ""))
        cat_id = cat_mapping.get(service_code)
        if cat_id is None:
            continue
        
        sales_amt = row.get("THSMON_SELNG_AMT")
        sales_cnt = row.get("THSMON_SELNG_CO")
        
        execute_sql(
            """
            INSERT INTO fact_sales_area_qtr (area_id, qtr, cat_id, sales_amt, sales_cnt)
            VALUES (:area_id, :qtr, :cat_id, :sales_amt, :sales_cnt)
            ON CONFLICT (area_id, qtr, cat_id) DO UPDATE SET
                sales_amt = EXCLUDED.sales_amt,
                sales_cnt = EXCLUDED.sales_cnt
            """,
            {
                "area_id": area_id,
                "qtr": qtr,
                "cat_id": cat_id,
                "sales_amt": int(sales_amt) if sales_amt else None,
                "sales_cnt": int(sales_cnt) if sales_cnt else None,
            },
        )
        upserted += 1
    
    return upserted


def main() -> None:
    print("=" * 60)
    print("Load D1 (추정매출) via API → fact_sales_area_qtr")
    print("=" * 60)
    
    quarters = TARGET_QUARTERS
    if len(sys.argv) > 1:
        quarters = sys.argv[1:]
        print(f"[INFO] Using custom quarters: {quarters}")
    
    commercial_codes = get_seongsu_commercial_codes()
    if not commercial_codes:
        print("\n[ERROR] No commercial areas in dim_area. Run load_boundaries first.")
        sys.exit(1)
    print(f"\n[Step 1] Seongsu commercial codes: {len(commercial_codes)}")
    
    area_mapping = get_area_id_mapping()
    print(f"[Step 2] Area mapping loaded: {len(area_mapping)} areas")
    
    collector = SeoulAPICollector()
    service = API_SERVICES["D1_SALES"]
    
    total_upserted = 0
    cat_mapping: dict[str, int] = {}
    
    for qtr in quarters:
        print(f"\n[Step 3] Fetching quarter {qtr} from Seoul API...")
        
        rows = collector.fetch_all(service, extra_params=[qtr])
        print(f"  Total rows fetched: {len(rows):,}")
        
        if not rows:
            print(f"  [INFO] No data for quarter {qtr}")
            continue
        
        seongsu_rows = [r for r in rows if str(r.get("TRDAR_CD", "")) in commercial_codes]
        print(f"  Seongsu rows: {len(seongsu_rows):,}")
        
        if not seongsu_rows:
            continue
        
        cat_mapping.update(upsert_dim_category(seongsu_rows))
        upserted = upsert_fact_sales(seongsu_rows, qtr, commercial_codes, area_mapping, cat_mapping)
        print(f"  Upserted: {upserted:,}")
        total_upserted += upserted
    
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)
    
    result = execute_sql("SELECT count(*) FROM fact_sales_area_qtr")
    count = list(result)[0][0]
    print(f"  fact_sales_area_qtr: {count:,} rows")
    
    result = execute_sql(
        """
        SELECT qtr, count(*) as cnt
        FROM fact_sales_area_qtr
        GROUP BY qtr
        ORDER BY qtr DESC
        LIMIT 8
        """
    )
    print("\n  Quarters coverage:")
    for row in result:
        print(f"    {row[0]}: {row[1]} rows")
    
    if total_upserted > 0:
        print(f"\n✓ Done! Total upserted: {total_upserted:,}")
    else:
        print("\n✗ Warning: No data loaded")


if __name__ == "__main__":
    main()
