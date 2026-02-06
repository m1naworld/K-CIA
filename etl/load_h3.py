"""Main script: H3 polyfill (res=10) → bridge_area_h3_weight.

Usage:
    python -m etl.load_h3
"""

from etl.db import execute_sql
from etl.processors.h3_mapper import (
    H3_RESOLUTION,
    compute_h3_weights,
    load_areas_from_db,
    upsert_bridge_h3,
)


def main() -> None:
    print("=" * 60)
    print(f"M1-3: H3 polyfill (res={H3_RESOLUTION}) → bridge_area_h3_weight")
    print("=" * 60)

    # Load areas
    areas = load_areas_from_db()
    print(f"\nLoaded {len(areas)} areas from dim_area")

    # Process each area
    all_records: list[dict] = []
    for area in areas:
        records = compute_h3_weights(area["area_id"], area["geom"])
        print(f"  {area['area_type']:20s} | {area['area_name']:15s} → {len(records)} hexes")
        all_records.extend(records)

    # Upsert
    print(f"\nUpserting {len(all_records)} records...")
    count = upsert_bridge_h3(all_records)
    print(f"  Inserted/updated: {count}")

    # Verification
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    result = execute_sql(
        "SELECT count(DISTINCT h3_index) FROM bridge_area_h3_weight"
    )
    distinct_h3 = list(result)[0][0]
    print(f"  Distinct H3 indices: {distinct_h3}")

    result = execute_sql(
        "SELECT da.area_type, count(*) as bridge_rows, count(DISTINCT b.h3_index) as unique_h3 "
        "FROM bridge_area_h3_weight b "
        "JOIN dim_area da ON b.area_id = da.area_id "
        "GROUP BY da.area_type"
    )
    for row in result:
        print(f"  {row[0]}: {row[1]} bridge rows, {row[2]} unique H3")

    result = execute_sql(
        "SELECT da.area_name, count(*) as hex_count, round(avg(b.weight)::numeric, 4) as avg_weight "
        "FROM bridge_area_h3_weight b "
        "JOIN dim_area da ON b.area_id = da.area_id "
        "GROUP BY da.area_name ORDER BY hex_count DESC LIMIT 10"
    )
    print("\n  Top 10 areas by hex count:")
    for row in result:
        print(f"    {row[0]:20s} | {row[1]:4d} hexes | avg_weight={row[2]}")

    dod_pass = distinct_h3 > 50
    print(f"\n  DoD check (distinct H3 > 50): {'PASS' if dod_pass else 'FAIL'} ({distinct_h3})")
    print("\nDone!")


if __name__ == "__main__":
    main()
