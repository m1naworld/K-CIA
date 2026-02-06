"""CRS conversion, geometry validation, normalization utilities."""

import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon
from shapely.validation import make_valid

from etl.config import CRS_WGS84


def ensure_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reproject to WGS84 (EPSG:4326) if needed."""
    if gdf.crs is None:
        print("[WARN] No CRS detected, assuming EPSG:4326")
        gdf = gdf.set_crs(CRS_WGS84)
    elif gdf.crs.to_epsg() != 4326:
        print(f"[CRS] Converting from {gdf.crs} → EPSG:4326")
        gdf = gdf.to_crs(CRS_WGS84)
    return gdf


def normalize_geometry(geom) -> MultiPolygon | None:
    """Convert Polygon → MultiPolygon, fix invalid geometries."""
    if geom is None or geom.is_empty:
        return None
    geom = make_valid(geom)
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    if isinstance(geom, MultiPolygon):
        return geom
    # GeometryCollection 등에서 Polygon만 추출
    polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
    if not polys:
        return None
    flat = []
    for p in polys:
        if isinstance(p, MultiPolygon):
            flat.extend(p.geoms)
        else:
            flat.append(p)
    return MultiPolygon(flat) if flat else None
