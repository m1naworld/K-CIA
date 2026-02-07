"""Portfolio API endpoints for multi-store management (Phase 5 S7/S8)."""

from __future__ import annotations

import json
from statistics import mean, stdev

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

import h3

from db import get_db
from api.schemas import (
    AssetInput,
    AssetHealth,
    PortfolioMatrix,
    ABComparison,
)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _compute_health(
    db: Session,
    h3_index: str,
    area_id: int | None,
    category: str | None,
) -> dict:
    """Compute health metrics for a location using k-ring(1) neighbors."""
    if not h3_index or not h3.is_valid_cell(h3_index):
        return {"health_score": 0, "health_status": "yellow", "factors": []}

    # Get the surrounding hexagons (k=1 ring)
    neighbors = list(h3.grid_disk(h3_index, 1))

    # Find area_ids for these hexagons
    rows = db.execute(text("""
        SELECT DISTINCT bw.area_id
        FROM bridge_area_h3_weight bw
        WHERE bw.h3_index = ANY(:h3s)
    """), {"h3s": neighbors}).fetchall()

    if not rows:
        return {"health_score": 0, "health_status": "yellow", "factors": ["주변 데이터 없음"]}

    area_ids = tuple(r.area_id for r in rows)

    # Get latest quarters
    qtrs = db.execute(text("""
        SELECT 'sales' AS tbl, MAX(qtr) AS qtr FROM fact_sales_area_qtr
        UNION ALL SELECT 'flow', MAX(qtr) FROM fact_flow_area_qtr
        UNION ALL SELECT 'store', MAX(qtr) FROM fact_store_area_qtr
    """)).fetchall()
    latest = {r.tbl: r.qtr for r in qtrs if r.qtr}

    sales_qtr = latest.get("sales", "")
    flow_qtr = latest.get("flow", "")
    store_qtr = latest.get("store", "")

    # Sales data
    cat_filter = ""
    params: dict = {"aids": area_ids, "qtr": sales_qtr}
    if category:
        cat_filter = "AND cat_id = (SELECT cat_id FROM dim_category WHERE service_code = :cat)"
        params["cat"] = category

    sales = db.execute(text(f"""
        SELECT SUM(sales_amt) AS total_sales
        FROM fact_sales_area_qtr
        WHERE area_id IN :aids AND qtr = :qtr {cat_filter}
    """), params).scalar() or 0

    # Flow data
    flow = db.execute(text("""
        SELECT SUM(flow_total) AS total_flow
        FROM fact_flow_area_qtr
        WHERE area_id IN :aids AND qtr = :qtr
    """), {"aids": area_ids, "qtr": flow_qtr}).scalar() or 0

    # Store data
    store_row = db.execute(text(f"""
        SELECT SUM(store_cnt) AS stores, SUM(close_cnt) AS closes
        FROM fact_store_area_qtr
        WHERE area_id IN :aids AND qtr = :qtr {cat_filter}
    """), {"aids": area_ids, "qtr": store_qtr}).fetchone()
    stores = store_row.stores or 0 if store_row else 0
    closes = store_row.closes or 0 if store_row else 0

    # Compute z-like scores (normalized 0-1)
    demand = min(float(sales) / 1e9, 1.0) * 0.5 + min(float(flow) / 1e6, 1.0) * 0.5
    competition = min(float(stores) / 200, 1.0)
    close_risk = min(float(closes) / max(float(stores), 1) * 5, 1.0)

    health_score = max(0, min(1, demand * 0.4 - competition * 0.2 - close_risk * 0.2 + 0.3))

    factors = []
    if demand > 0.5:
        factors.append(f"높은 수요 (매출 {float(sales)/1e8:.1f}억원)")
    if competition > 0.5:
        factors.append(f"경쟁 과밀 (점포 {stores}개)")
    if close_risk > 0.3:
        factors.append(f"폐업 리스크 (폐업 {closes}건)")

    status = "green" if health_score > 0.6 else ("red" if health_score < 0.3 else "yellow")

    return {
        "health_score": round(health_score, 3),
        "health_status": status,
        "demand_z": round(demand, 3),
        "competition_z": round(competition, 3),
        "growth_z": 0.0,
        "risk_z": round(close_risk, 3),
        "factors": factors,
    }


@router.post("/assets")
def register_asset(asset: AssetInput, db: Session = Depends(get_db)):
    """Register a store/asset and compute its H3 index."""
    if not asset.lat or not asset.lng:
        raise HTTPException(status_code=400, detail="lat and lng are required")

    h3_index = h3.latlng_to_cell(asset.lat, asset.lng, 10)

    # Find nearest area
    area_row = db.execute(text("""
        SELECT bw.area_id, da.area_name
        FROM bridge_area_h3_weight bw
        JOIN dim_area da ON da.area_id = bw.area_id
        WHERE bw.h3_index = :h3
        ORDER BY bw.weight DESC
        LIMIT 1
    """), {"h3": h3_index}).fetchone()

    area_id = area_row.area_id if area_row else None

    result = db.execute(text("""
        INSERT INTO dim_asset (address, lat, lng, h3_index, area_id, category)
        VALUES (:addr, :lat, :lng, :h3, :aid, :cat)
        RETURNING asset_id
    """), {
        "addr": asset.address,
        "lat": asset.lat,
        "lng": asset.lng,
        "h3": h3_index,
        "aid": area_id,
        "cat": asset.category,
    })
    db.commit()

    return {
        "asset_id": result.scalar(),
        "h3_index": h3_index,
        "area_name": area_row.area_name if area_row else None,
    }


@router.get("/health", response_model=PortfolioMatrix)
def get_portfolio_health(
    user_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Get health cards for all registered assets."""
    query = "SELECT * FROM dim_asset"
    params: dict = {}
    if user_id:
        query += " WHERE user_id = :uid"
        params["uid"] = user_id
    query += " ORDER BY asset_id"

    assets = db.execute(text(query), params).fetchall()

    healths = []
    for a in assets:
        metrics = _compute_health(db, a.h3_index, a.area_id, a.category)
        healths.append(AssetHealth(
            asset_id=a.asset_id,
            address=a.address,
            area_name=None,
            health_status=metrics["health_status"],
            health_score=metrics["health_score"],
            demand_z=metrics.get("demand_z"),
            competition_z=metrics.get("competition_z"),
            growth_z=metrics.get("growth_z"),
            risk_z=metrics.get("risk_z"),
            top_factors=metrics.get("factors", []),
        ))

    suggestions = []
    reds = [h for h in healths if h.health_status == "red"]
    greens = [h for h in healths if h.health_status == "green"]
    if reds:
        suggestions.append(f"경고 점포 {len(reds)}곳: 철수 또는 운영 개선 검토 필요")
    if greens:
        suggestions.append(f"우수 점포 {len(greens)}곳: 확장 또는 투자 강화 검토")
    if len(healths) > 1:
        scores = [h.health_score for h in healths]
        if stdev(scores) > 0.2:
            suggestions.append("점포 간 건강도 편차가 큽니다. 포트폴리오 리밸런싱을 검토하세요.")

    return PortfolioMatrix(assets=healths, rebalance_suggestions=suggestions)


@router.post("/compare", response_model=ABComparison)
def compare_assets(
    asset_a_id: int,
    asset_b_id: int,
    db: Session = Depends(get_db),
):
    """Compare two assets side by side."""
    a = db.execute(text("SELECT * FROM dim_asset WHERE asset_id = :id"), {"id": asset_a_id}).fetchone()
    b = db.execute(text("SELECT * FROM dim_asset WHERE asset_id = :id"), {"id": asset_b_id}).fetchone()

    if not a or not b:
        raise HTTPException(status_code=404, detail="Asset not found")

    ma = _compute_health(db, a.h3_index, a.area_id, a.category)
    mb = _compute_health(db, b.h3_index, b.area_id, b.category)

    health_a = AssetHealth(
        asset_id=a.asset_id, address=a.address, health_status=ma["health_status"],
        health_score=ma["health_score"], demand_z=ma.get("demand_z"),
        competition_z=ma.get("competition_z"), risk_z=ma.get("risk_z"),
        top_factors=ma.get("factors", []),
    )
    health_b = AssetHealth(
        asset_id=b.asset_id, address=b.address, health_status=mb["health_status"],
        health_score=mb["health_score"], demand_z=mb.get("demand_z"),
        competition_z=mb.get("competition_z"), risk_z=mb.get("risk_z"),
        top_factors=mb.get("factors", []),
    )

    if ma["health_score"] > mb["health_score"]:
        rec = f"A({a.address})가 더 안정적입니다 (건강도 {ma['health_score']:.2f} vs {mb['health_score']:.2f})"
    else:
        rec = f"B({b.address})가 더 안정적입니다 (건강도 {mb['health_score']:.2f} vs {ma['health_score']:.2f})"

    return ABComparison(
        asset_a=health_a,
        asset_b=health_b,
        recommendation=rec,
        sensitivity={
            "note": "임대료/공실 민감도 분석은 D14/D15 데이터 적재 후 제공됩니다",
        },
    )
