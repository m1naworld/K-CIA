"""Read D9 (행정동 SHP) and fetch D3 (상권영역) via API + SHP hybrid."""

from __future__ import annotations

import math
from pathlib import Path

import chardet
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Polygon

from etl.collectors.seoul_api_collector import SeoulAPICollector
from etl.config import CRS_KOREA, D3_DIR, D9_DIR, SEONGSU_ADSTRD_CODES


# ── D9 SHP helpers ────────────────────────────────────────────


def _detect_encoding(dbf_path: Path) -> str:
    """Detect encoding of a .dbf file."""
    with open(dbf_path, "rb") as f:
        raw = f.read(min(100_000, dbf_path.stat().st_size))
    result = chardet.detect(raw)
    return result.get("encoding", "cp949") or "cp949"


def _find_shp(directory: Path) -> Path:
    """Find the first .shp file in a directory (recursive)."""
    shps = list(directory.rglob("*.shp"))
    if not shps:
        raise FileNotFoundError(f"No .shp file found in {directory}")
    if len(shps) > 1:
        print(f"[WARN] Multiple .shp files found, using: {shps[0]}")
    return shps[0]


def _read_shp_with_encoding(shp_path: Path, encodings: list[str]) -> gpd.GeoDataFrame:
    """Read SHP trying multiple encodings via pyogrio ENCODING open option."""
    for enc in encodings:
        try:
            gdf = gpd.read_file(
                shp_path,
                engine="pyogrio",
                open_options={"ENCODING": enc},
            )
            print(f"  Loaded {len(gdf)} rows with encoding={enc}")
            print(f"  Columns: {list(gdf.columns)}")
            return gdf
        except Exception:
            continue

    # chardet fallback
    dbf_path = shp_path.with_suffix(".dbf")
    detected = _detect_encoding(dbf_path) if dbf_path.exists() else "utf-8"
    print(f"  Trying chardet-detected encoding: {detected}")
    gdf = gpd.read_file(
        shp_path,
        engine="pyogrio",
        open_options={"ENCODING": detected},
    )
    print(f"  Loaded {len(gdf)} rows with encoding={detected}")
    print(f"  Columns: {list(gdf.columns)}")
    return gdf


def read_d9_shp() -> gpd.GeoDataFrame:
    """Read D9 administrative boundary SHP with encoding fallback."""
    shp_path = _find_shp(D9_DIR)
    print(f"[D9] Reading: {shp_path}")
    return _read_shp_with_encoding(shp_path, ["cp949", "euc-kr"])


def read_d3_shp() -> gpd.GeoDataFrame | None:
    """Read D3 commercial area SHP if available."""
    if not D3_DIR.exists() or not list(D3_DIR.rglob("*.shp")):
        return None
    shp_path = _find_shp(D3_DIR)
    print(f"[D3-SHP] Reading: {shp_path}")
    return _read_shp_with_encoding(shp_path, ["utf-8", "cp949", "euc-kr"])


# ── D3 API ────────────────────────────────────────────────────


def _circle_polygon(cx: float, cy: float, area_sqm: float, n_points: int = 32) -> Polygon:
    """Create a circular polygon from center + area (in EPSG:5181 meters)."""
    radius = math.sqrt(area_sqm / math.pi)
    angles = np.linspace(0, 2 * math.pi, n_points, endpoint=False)
    coords = [(cx + radius * math.cos(a), cy + radius * math.sin(a)) for a in angles]
    coords.append(coords[0])  # close ring
    return Polygon(coords)


def fetch_d3_api_seongsu() -> list[dict]:
    """Fetch D3 commercial areas for Seongsu-dong via Seoul Open API.

    Uses TbgisTrdarRelm service and filters by ADSTRD_CD.
    """
    collector = SeoulAPICollector()
    print("[D3-API] Fetching from Seoul Open API (TbgisTrdarRelm)...")
    rows = collector.fetch_all("TbgisTrdarRelm")
    print(f"[D3-API] Total records: {len(rows)}")

    # Filter Seongsu-dong
    seongsu = [
        r for r in rows
        if r.get("ADSTRD_CD", "") in SEONGSU_ADSTRD_CODES
    ]
    print(f"[D3-API] Seongsu-dong commercial areas: {len(seongsu)}")
    for r in seongsu:
        print(f"  {r['TRDAR_CD']} {r['TRDAR_CD_NM']} ({r['TRDAR_SE_CD_NM']})")
    return seongsu


def build_d3_hybrid(
    api_rows: list[dict],
    shp_gdf: gpd.GeoDataFrame | None,
) -> gpd.GeoDataFrame:
    """Build D3 GeoDataFrame: SHP polygon where available, API circle buffer as fallback.

    Args:
        api_rows: Filtered API rows (Seongsu-dong only)
        shp_gdf: Full SHP GeoDataFrame (or None if SHP unavailable)

    Returns:
        GeoDataFrame in EPSG:5181 with TRDAR_CD, TRDAR_CD_NM, geometry, source columns
    """
    # Build SHP lookup by TRDAR_CD
    shp_lookup: dict[str, object] = {}
    shp_code_col = None
    if shp_gdf is not None and len(shp_gdf) > 0:
        # Find TRDAR_CD column in SHP
        for cand in ["TRDAR_CD", "상권_코드", "TRDAREA_CD"]:
            if cand in shp_gdf.columns:
                shp_code_col = cand
                break
        if shp_code_col:
            for _, row in shp_gdf.iterrows():
                code = str(row[shp_code_col])
                shp_lookup[code] = row.geometry
            print(f"[D3-Hybrid] SHP lookup built: {len(shp_lookup)} entries (col={shp_code_col})")

    records = []
    from_shp = 0
    from_api = 0

    for r in api_rows:
        code = str(r["TRDAR_CD"])
        name = r["TRDAR_CD_NM"]

        if code in shp_lookup and shp_lookup[code] is not None and not shp_lookup[code].is_empty:
            geom = shp_lookup[code]
            source = "shp"
            from_shp += 1
        else:
            # Circle buffer from API center + area
            cx = float(r.get("XCNTS_VALUE", 0))
            cy = float(r.get("YDNTS_VALUE", 0))
            area = float(r.get("RELM_AR", 0))
            if cx == 0 or cy == 0 or area == 0:
                print(f"  [WARN] Skipping {name} ({code}): no coordinates/area")
                continue
            geom = _circle_polygon(cx, cy, area)
            source = "api_buffer"
            from_api += 1

        records.append({
            "TRDAR_CD": code,
            "TRDAR_CD_NM": name,
            "TRDAR_SE_CD_NM": r.get("TRDAR_SE_CD_NM", ""),
            "geometry": geom,
            "source": source,
        })

    gdf = gpd.GeoDataFrame(records, crs=CRS_KOREA)
    print(f"[D3-Hybrid] Result: {len(gdf)} areas (SHP: {from_shp}, API buffer: {from_api})")
    return gdf
