"""Export D9 행정동 + D3 상권 boundaries to GeoJSON for frontend map display.

Usage:
    source backend/venv/bin/activate
    python -m etl.export_boundaries_geojson
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd

from etl.config import CRS_WGS84, D3_DIR, D9_DIR, SEONGSU_ADSTRD_CODES

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public" / "data"

# 행정동코드 매핑 (8자리 SHP ADM_CD → 행정동명)
SEONGSU_DONG_MAP = {
    "11040650": "성수1가1동",
    "11040660": "성수1가2동",
    "11040670": "성수2가1동",
    "11040680": "성수2가3동",
}

# ADSTRD_CD(8자리) → ADM_CD(8자리) 매핑
ADSTRD_TO_ADM = {
    "11200650": "11040650",
    "11200660": "11040660",
    "11200670": "11040670",
    "11200690": "11040680",
}

ADSTRD_TO_DONG_NAME = {
    "11200650": "성수1가1동",
    "11200660": "성수1가2동",
    "11200670": "성수2가1동",
    "11200690": "성수2가3동",
}


def export_admin_dong() -> None:
    """Export D9 행정동 4개 → admin_dong.geojson."""
    shp_path = next(D9_DIR.rglob("*.shp"))
    gdf = gpd.read_file(shp_path, engine="pyogrio", open_options={"ENCODING": "cp949"})

    seongsu = gdf[gdf["ADM_CD"].isin(SEONGSU_DONG_MAP.keys())].copy()
    seongsu = seongsu.to_crs(CRS_WGS84)

    features = []
    for _, row in seongsu.iterrows():
        code = row["ADM_CD"]
        features.append({
            "type": "Feature",
            "properties": {
                "code": code,
                "name": SEONGSU_DONG_MAP.get(code, row["ADM_NM"]),
            },
            "geometry": json.loads(gpd.GeoSeries([row.geometry], crs=CRS_WGS84).to_json())["features"][0]["geometry"],
        })

    geojson = {"type": "FeatureCollection", "features": features}
    out = OUTPUT_DIR / "admin_dong.geojson"
    out.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(features)} 행정동 → {out}")


def export_commercial_areas() -> None:
    """Export D3 상권 17개 → commercial_areas.geojson."""
    shp_path = next(D3_DIR.rglob("*.shp"))
    gdf = gpd.read_file(shp_path, engine="pyogrio", open_options={"ENCODING": "utf-8"})

    seongsu = gdf[gdf["ADSTRD_CD"].isin(SEONGSU_ADSTRD_CODES)].copy()
    seongsu = seongsu.to_crs(CRS_WGS84)

    features = []
    for _, row in seongsu.iterrows():
        features.append({
            "type": "Feature",
            "properties": {
                "code": str(row["TRDAR_CD"]),
                "name": row["TRDAR_CD_N"],
                "type": row["TRDAR_SE_1"],  # 골목상권/발달상권/전통시장
                "type_code": row["TRDAR_SE_C"],
                "admin_dong": ADSTRD_TO_DONG_NAME.get(row["ADSTRD_CD"], row["ADSTRD_CD_"]),
            },
            "geometry": json.loads(gpd.GeoSeries([row.geometry], crs=CRS_WGS84).to_json())["features"][0]["geometry"],
        })

    geojson = {"type": "FeatureCollection", "features": features}
    out = OUTPUT_DIR / "commercial_areas.geojson"
    out.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(features)} 상권 → {out}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 50)
    print("Exporting boundary GeoJSON for frontend")
    print("=" * 50)
    export_admin_dong()
    export_commercial_areas()
    print("\nDone!")


if __name__ == "__main__":
    main()
