"""Filter Seongsu-dong areas and upsert into dim_area + preset_area_scope."""

import geopandas as gpd
from geoalchemy2.shape import from_shape
from sqlalchemy import text

from etl.config import (
    COMMERCIAL_CODE_CANDIDATES,
    COMMERCIAL_NAME_CANDIDATES,
    DONG_CODE_CANDIDATES,
    DONG_NAME_CANDIDATES,
    SEONGSU_DONG_CODES,
    SEONGSU_DONG_NAMES,
)
from etl.db import engine
from etl.processors.spatial_utils import ensure_wgs84, normalize_geometry


def _find_column(columns: list[str], candidates: list[str]) -> str | None:
    """Find the first matching column from candidates."""
    col_lower = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in col_lower:
            return col_lower[cand.lower()]
    return None


def filter_seongsu_dong(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Filter D9 GeoDataFrame to Seongsu-dong 4 areas."""
    # Try name-based filter first
    name_col = _find_column(list(gdf.columns), DONG_NAME_CANDIDATES)
    code_col = _find_column(list(gdf.columns), DONG_CODE_CANDIDATES)

    if name_col:
        mask = gdf[name_col].isin(SEONGSU_DONG_NAMES)
        filtered = gdf[mask].copy()
        if len(filtered) > 0:
            print(f"[D9] Filtered by {name_col}: {len(filtered)} rows")
            return filtered
        # 부분 매칭 시도 (성수 포함)
        mask = gdf[name_col].str.contains("성수", na=False)
        filtered = gdf[mask].copy()
        if len(filtered) > 0:
            print(f"[D9] Filtered by '성수' in {name_col}: {len(filtered)} rows")
            return filtered

    if code_col:
        mask = gdf[code_col].astype(str).isin(SEONGSU_DONG_CODES)
        filtered = gdf[mask].copy()
        if len(filtered) > 0:
            print(f"[D9] Filtered by {code_col}: {len(filtered)} rows")
            return filtered

    raise ValueError(
        f"Cannot filter Seongsu-dong. Columns: {list(gdf.columns)}. "
        f"Tried name cols: {DONG_NAME_CANDIDATES}, code cols: {DONG_CODE_CANDIDATES}"
    )


def filter_seongsu_commercial(
    d3_gdf: gpd.GeoDataFrame,
    dong_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Filter D3 commercial areas that intersect Seongsu-dong polygon union."""
    dong_gdf = ensure_wgs84(dong_gdf)
    d3_gdf = ensure_wgs84(d3_gdf)

    seongsu_union = dong_gdf.union_all()
    # spatial intersection
    mask = d3_gdf.geometry.intersects(seongsu_union)
    filtered = d3_gdf[mask].copy()
    print(f"[D3] Filtered by spatial intersection: {len(filtered)} commercial areas")

    if len(filtered) == 0:
        # bbox fallback
        print("[D3] Trying bbox overlap fallback...")
        bbox = seongsu_union.bounds  # (minx, miny, maxx, maxy)
        from shapely.geometry import box

        bbox_geom = box(*bbox).buffer(0.005)  # ~500m buffer
        mask = d3_gdf.geometry.intersects(bbox_geom)
        filtered = d3_gdf[mask].copy()
        print(f"[D3] Bbox fallback: {len(filtered)} commercial areas")

    return filtered


def upsert_dim_area(
    gdf: gpd.GeoDataFrame,
    area_type: str,
    code_col: str,
    name_col: str,
) -> list[int]:
    """Upsert rows into dim_area. Returns list of area_ids."""
    gdf = ensure_wgs84(gdf)

    upsert_sql = text("""
        INSERT INTO dim_area (area_type, area_code, area_name, geom)
        VALUES (:area_type, :area_code, :area_name, ST_GeomFromText(:geom, 4326))
        ON CONFLICT (area_type, area_code) DO UPDATE
        SET area_name = EXCLUDED.area_name,
            geom = EXCLUDED.geom
        RETURNING area_id
    """)

    area_ids = []
    with engine.begin() as conn:
        for _, row in gdf.iterrows():
            geom = normalize_geometry(row.geometry)
            if geom is None:
                print(f"[WARN] Skipping {row[code_col]}: invalid geometry")
                continue

            result = conn.execute(
                upsert_sql,
                {
                    "area_type": area_type,
                    "area_code": str(row[code_col]),
                    "area_name": str(row[name_col]),
                    "geom": geom.wkt,
                },
            )
            area_id = result.scalar()
            area_ids.append(area_id)
            print(f"  [{area_type}] {row[name_col]} ({row[code_col]}) → area_id={area_id}")

    print(f"[dim_area] Upserted {len(area_ids)} rows for {area_type}")
    return area_ids


def load_preset_area_scope():
    """Populate preset_area_scope from all dim_area rows."""
    sql = text("""
        INSERT INTO preset_area_scope (area_id, area_type)
        SELECT area_id, area_type FROM dim_area
        ON CONFLICT DO NOTHING
    """)
    # preset_area_scope has no unique constraint yet, truncate first
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM preset_area_scope"))
        result = conn.execute(sql)
        print(f"[preset_area_scope] Loaded {result.rowcount} rows")


def resolve_columns(
    gdf: gpd.GeoDataFrame,
    code_candidates: list[str],
    name_candidates: list[str],
) -> tuple[str, str]:
    """Resolve code and name column from GeoDataFrame."""
    code_col = _find_column(list(gdf.columns), code_candidates)
    name_col = _find_column(list(gdf.columns), name_candidates)
    if not code_col or not name_col:
        raise ValueError(
            f"Cannot find code/name columns. "
            f"Available: {list(gdf.columns)}, "
            f"Tried code: {code_candidates}, name: {name_candidates}"
        )
    return code_col, name_col
