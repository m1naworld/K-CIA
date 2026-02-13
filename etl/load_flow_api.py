"""Load D5 (유동인구-상권) via Seoul Open API → fact_flow_area_qtr.

Usage:
    docker compose run --rm --entrypoint python etl -m etl.load_flow_api
    docker compose run --rm --entrypoint python etl -m etl.load_flow_api 20244
"""

from __future__ import annotations

import json
import sys
from typing import Any

from etl.collectors.seoul_api_collector import SeoulAPICollector, API_SERVICES
from etl.db import execute_sql

TARGET_QUARTERS = ["20253", "20252", "20251", "20244", "20243", "20242", "20241"]


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


def upsert_fact_flow(
    rows: list[dict[str, Any]],
    commercial_codes: set[str],
    area_mapping: dict[str, int],
) -> int:
    """Upsert flow data to fact_flow_area_qtr."""
    upserted = 0
    
    for row in rows:
        commercial_code = str(row.get("TRDAR_CD", ""))
        
        if commercial_code not in commercial_codes:
            continue
        
        area_id = area_mapping.get(commercial_code)
        if area_id is None:
            continue
        
        qtr = str(row.get("STDR_YYQU_CD", ""))
        if not qtr:
            continue
        
        flow_total = row.get("TOT_FLPOP_CO")
        
        flow_by_hour = {
            "00_06": row.get("TMZON_00_06_FLPOP_CO"),
            "06_11": row.get("TMZON_06_11_FLPOP_CO"),
            "11_14": row.get("TMZON_11_14_FLPOP_CO"),
            "14_17": row.get("TMZON_14_17_FLPOP_CO"),
            "17_21": row.get("TMZON_17_21_FLPOP_CO"),
            "21_24": row.get("TMZON_21_24_FLPOP_CO"),
        }
        
        flow_by_weekday = {
            "mon": row.get("MON_FLPOP_CO"),
            "tue": row.get("TUES_FLPOP_CO"),
            "wed": row.get("WED_FLPOP_CO"),
            "thu": row.get("THUR_FLPOP_CO"),
            "fri": row.get("FRI_FLPOP_CO"),
            "sat": row.get("SAT_FLPOP_CO"),
            "sun": row.get("SUN_FLPOP_CO"),
        }
        
        flow_by_demo = {
            "male": row.get("ML_FLPOP_CO"),
            "female": row.get("FML_FLPOP_CO"),
            "age_10": row.get("AGRDE_10_FLPOP_CO"),
            "age_20": row.get("AGRDE_20_FLPOP_CO"),
            "age_30": row.get("AGRDE_30_FLPOP_CO"),
            "age_40": row.get("AGRDE_40_FLPOP_CO"),
            "age_50": row.get("AGRDE_50_FLPOP_CO"),
            "age_60+": row.get("AGRDE_60_ABOVE_FLPOP_CO"),
        }
        
        execute_sql(
            """
            INSERT INTO fact_flow_area_qtr (area_id, qtr, flow_total, flow_by_hour, flow_by_weekday, flow_by_demo)
            VALUES (:area_id, :qtr, :flow_total, :flow_by_hour, :flow_by_weekday, :flow_by_demo)
            ON CONFLICT (area_id, qtr) DO UPDATE SET
                flow_total = EXCLUDED.flow_total,
                flow_by_hour = EXCLUDED.flow_by_hour,
                flow_by_weekday = EXCLUDED.flow_by_weekday,
                flow_by_demo = EXCLUDED.flow_by_demo
            """,
            {
                "area_id": area_id,
                "qtr": qtr,
                "flow_total": int(flow_total) if flow_total else None,
                "flow_by_hour": json.dumps(flow_by_hour),
                "flow_by_weekday": json.dumps(flow_by_weekday),
                "flow_by_demo": json.dumps(flow_by_demo),
            },
        )
        upserted += 1
    
    return upserted


def main() -> None:
    print("=" * 60)
    print("Load D5 (유동인구) via API → fact_flow_area_qtr")
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
    service = API_SERVICES["D5_FLOW"]
    
    total_upserted = 0
    
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
        
        upserted = upsert_fact_flow(seongsu_rows, commercial_codes, area_mapping)
        print(f"  Upserted: {upserted:,}")
        total_upserted += upserted
    
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)
    
    result = execute_sql("SELECT count(*) FROM fact_flow_area_qtr")
    count = list(result)[0][0]
    print(f"  fact_flow_area_qtr: {count:,} rows")
    
    result = execute_sql(
        """
        SELECT qtr, count(*) as cnt, sum(flow_total) as total_flow
        FROM fact_flow_area_qtr
        GROUP BY qtr
        ORDER BY qtr DESC
        LIMIT 8
        """
    )
    print("\n  Quarters coverage:")
    for row in result:
        flow = f"{row[2]:,}" if row[2] else "N/A"
        print(f"    {row[0]}: {row[1]} rows, flow={flow}")
    
    if total_upserted > 0:
        print(f"\n✓ Done! Total upserted: {total_upserted:,}")
    else:
        print("\n✗ Warning: No data loaded")


if __name__ == "__main__":
    main()
