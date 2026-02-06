"""Main script: Load D9 (행정동 SHP) + D3 (상권영역 API+SHP hybrid) → dim_area + preset_area_scope.

Usage:
    python -m etl.load_boundaries
"""

import sys

from etl.collectors.boundary_collector import (
    build_d3_hybrid,
    fetch_d3_api_seongsu,
    read_d3_shp,
    read_d9_shp,
)
from etl.config import (
    D9_DIR,
    DONG_CODE_CANDIDATES,
    DONG_NAME_CANDIDATES,
)
from etl.processors.area_loader import (
    filter_seongsu_dong,
    load_preset_area_scope,
    resolve_columns,
    upsert_dim_area,
)


def main() -> None:
    print("=" * 60)
    print("M1-2: Load D9 + D3 → dim_area")
    print("=" * 60)

    # ── Step 1: D9 행정동 ──────────────────────────────────────
    if not D9_DIR.exists() or not list(D9_DIR.rglob("*.shp")):
        print(f"[ERROR] D9 SHP not found in {D9_DIR}")
        print("  → 행정동 경계 SHP 파일을 다운로드해주세요.")
        sys.exit(1)

    print("\n[Step 1] Reading D9 SHP...")
    d9_gdf = read_d9_shp()

    print("\n[Step 2] Filtering Seongsu-dong...")
    seongsu_dong = filter_seongsu_dong(d9_gdf)

    dong_code_col, dong_name_col = resolve_columns(
        seongsu_dong, DONG_CODE_CANDIDATES, DONG_NAME_CANDIDATES
    )
    print(f"  code_col={dong_code_col}, name_col={dong_name_col}")

    print("\n[Step 3] Upserting ADMIN_DONG...")
    upsert_dim_area(seongsu_dong, "ADMIN_DONG", dong_code_col, dong_name_col)

    # ── Step 2: D3 상권영역 (API + SHP hybrid) ────────────────
    print("\n[Step 4] Fetching D3 from API...")
    try:
        api_rows = fetch_d3_api_seongsu()
    except Exception as e:
        print(f"[ERROR] D3 API failed: {e}")
        print("  → SEOUL_API_KEY 확인 필요. 상권영역 없이 진행합니다.")
        api_rows = []

    if api_rows:
        print("\n[Step 5] Reading D3 SHP (optional, for polygon matching)...")
        shp_gdf = read_d3_shp()
        if shp_gdf is not None:
            print(f"  SHP loaded: {len(shp_gdf)} rows")
        else:
            print("  SHP not available → API center+area buffer fallback")

        print("\n[Step 6] Building hybrid D3 GeoDataFrame...")
        d3_hybrid = build_d3_hybrid(api_rows, shp_gdf)

        if len(d3_hybrid) > 0:
            print("\n[Step 7] Upserting COMMERCIAL_AREA...")
            upsert_dim_area(
                d3_hybrid, "COMMERCIAL_AREA", "TRDAR_CD", "TRDAR_CD_NM"
            )
        else:
            print("[WARN] No commercial areas to upsert.")
    else:
        print("[WARN] No API data. Skipping D3.")

    # ── Step 3: preset_area_scope ──────────────────────────────
    print("\n[Step 8] Loading preset_area_scope...")
    load_preset_area_scope()

    # ── Verification ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    from etl.db import execute_sql

    result = execute_sql(
        "SELECT area_type, count(*), sum(ST_IsValid(geom)::int) as valid_count "
        "FROM dim_area GROUP BY area_type"
    )
    for row in result:
        print(f"  {row[0]}: {row[1]} rows, {row[2]} valid geometries")

    result = execute_sql("SELECT DISTINCT ST_SRID(geom) FROM dim_area WHERE geom IS NOT NULL")
    srids = [row[0] for row in result]
    print(f"  SRIDs: {srids}")

    result = execute_sql(
        "SELECT da.area_type, count(*) FROM preset_area_scope ps "
        "JOIN dim_area da ON ps.area_id = da.area_id GROUP BY da.area_type"
    )
    for row in result:
        print(f"  preset_area_scope [{row[0]}]: {row[1]}")

    print("\n✓ Done!")


if __name__ == "__main__":
    main()
