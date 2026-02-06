"""H3 polyfill: dim_area polygons → bridge_area_h3_weight (res=10).

For each area polygon:
1. Polyfill with h3 at resolution 10
2. Calculate weight as intersection_area / hex_area
3. Fallback: if polyfill returns 0 hexes, assign centroid hex with weight=1.0
"""

from __future__ import annotations

import h3
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.ops import unary_union

from etl.db import execute_sql


H3_RESOLUTION = 10


def _polyfill_multipolygon(geom: MultiPolygon, resolution: int) -> set[str]:
    """Polyfill a MultiPolygon and return set of H3 indices."""
    hexes: set[str] = set()
    for polygon in geom.geoms:
        geo_json = mapping(polygon)  # standard GeoJSON (lng, lat)
        hexes.update(h3.polyfill_geojson(geo_json, resolution))
    return hexes


def _h3_to_polygon(h3_index: str) -> Polygon:
    """Convert H3 index to shapely Polygon."""
    boundary = h3.h3_to_geo_boundary(h3_index, geo_json=True)
    return Polygon(boundary)


def compute_h3_weights(
    area_id: int,
    geom: MultiPolygon,
    resolution: int = H3_RESOLUTION,
) -> list[dict]:
    """Compute H3 hex weights for a single area polygon.

    Returns list of {"area_id", "h3_index", "weight"} dicts.
    """
    hexes = _polyfill_multipolygon(geom, resolution)

    # Fallback: centroid hex if polyfill returns nothing (small polygons)
    if not hexes:
        centroid = geom.centroid
        centroid_hex = h3.geo_to_h3(centroid.y, centroid.x, resolution)
        return [{"area_id": area_id, "h3_index": centroid_hex, "weight": 1.0}]

    results = []
    for h3_idx in hexes:
        hex_poly = _h3_to_polygon(h3_idx)
        intersection = geom.intersection(hex_poly)
        if intersection.is_empty:
            continue
        weight = intersection.area / hex_poly.area
        weight = min(weight, 1.0)  # cap at 1.0
        if weight > 0.001:  # skip negligible overlaps
            results.append({
                "area_id": area_id,
                "h3_index": h3_idx,
                "weight": round(weight, 6),
            })

    # Should not happen, but safety fallback
    if not results:
        centroid = geom.centroid
        centroid_hex = h3.geo_to_h3(centroid.y, centroid.x, resolution)
        results = [{"area_id": area_id, "h3_index": centroid_hex, "weight": 1.0}]

    return results


def load_areas_from_db() -> list[dict]:
    """Load area_id + geom from dim_area."""
    result = execute_sql(
        "SELECT area_id, area_name, area_type, ST_AsText(geom) as wkt "
        "FROM dim_area WHERE geom IS NOT NULL"
    )
    from shapely import wkt as shapely_wkt

    rows = []
    for row in result:
        geom = shapely_wkt.loads(row[3])
        if isinstance(geom, Polygon):
            geom = MultiPolygon([geom])
        rows.append({
            "area_id": row[0],
            "area_name": row[1],
            "area_type": row[2],
            "geom": geom,
        })
    return rows


def upsert_bridge_h3(records: list[dict]) -> int:
    """Insert H3 weight records into bridge_area_h3_weight (upsert)."""
    if not records:
        return 0

    from sqlalchemy import text
    from etl.db import engine

    sql = text(
        "INSERT INTO bridge_area_h3_weight (area_id, h3_index, weight) "
        "VALUES (:area_id, :h3_index, :weight) "
        "ON CONFLICT (area_id, h3_index) DO UPDATE SET weight = EXCLUDED.weight"
    )
    with engine.connect() as conn:
        for rec in records:
            conn.execute(sql, rec)
        conn.commit()
    return len(records)
