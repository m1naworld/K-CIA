"""Map API endpoints: hexagon grid and hexagon detail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

import h3

from db import get_db
from api.schemas import (
    CompetitionCard,
    FlowCard,
    GrowthCard,
    HexagonDetailResponse,
    HexagonSummary,
    HexagonsResponse,
    HeatmapHexagon,
    HeatmapResponse,
    PeaktimeAnalysis,
    RiskHexagon,
    RiskLayerResponse,
    RiskAnalysis,
    QuarterComparison,
    CompareResponse,
    RiskCard,
    SalesCard,
)

router = APIRouter(prefix="/api/map", tags=["map"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prev_quarter(qtr: str) -> str:
    """Return the previous quarter string. '20241' → '20234'."""
    year, q = int(qtr[:4]), int(qtr[-1])
    if q == 1:
        return f"{year - 1}4"
    return f"{year}{q - 1}"


def _latest_quarter(db: Session) -> str:
    """Return the most recent quarter available in fact_sales_area_qtr."""
    row = db.execute(
        text("SELECT MAX(qtr) FROM fact_sales_area_qtr")
    ).scalar()
    if not row:
        raise HTTPException(status_code=503, detail="No data available")
    return row


def _latest_quarters(db: Session) -> dict[str, str]:
    """Return the latest quarter per fact table."""
    rows = db.execute(text("""
        SELECT 'sales' AS tbl, MAX(qtr) AS qtr FROM fact_sales_area_qtr
        UNION ALL
        SELECT 'flow', MAX(qtr) FROM fact_flow_area_qtr
        UNION ALL
        SELECT 'store', MAX(qtr) FROM fact_store_area_qtr
    """)).fetchall()
    return {r.tbl: r.qtr for r in rows if r.qtr}


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return round((a - b) / b, 4)


# ---------------------------------------------------------------------------
# GET /api/map/hexagons
# ---------------------------------------------------------------------------

@router.get("/hexagons", response_model=HexagonsResponse)
def get_hexagons(
    area_type: str = Query("COMMERCIAL_AREA", regex="^(COMMERCIAL_AREA|ADMIN_DONG)$"),
    category: str | None = Query(None),
    qtr: str | None = Query(None),
    weight_type: str = Query("store", regex="^(store|area)$"),
    db: Session = Depends(get_db),
):
    qtrs = _latest_quarters(db)
    sales_qtr = qtr or qtrs.get("sales", "")
    flow_qtr = qtr or qtrs.get("flow", "")
    store_qtr = qtr or qtrs.get("store", "")

    cat_filter_sales = ""
    cat_filter_store = ""
    params: dict = {
        "area_type": area_type,
        "sales_qtr": sales_qtr,
        "flow_qtr": flow_qtr,
        "store_qtr": store_qtr,
    }
    if category:
        cat_filter_sales = "AND s.cat_id = (SELECT cat_id FROM dim_category WHERE service_code = :cat)"
        cat_filter_store = "AND st.cat_id = (SELECT cat_id FROM dim_category WHERE service_code = :cat)"
        params["cat"] = category

    # Select weight table based on weight_type parameter
    # store: 점포 수 기반 weight (fallback to area if no store data)
    # area: 면적 교차 비율 기반 weight
    if weight_type == "store":
        weight_cte = """
        weight_source AS (
            -- 점포 기반 weight, 없으면 면적 기반 fallback
            SELECT
                COALESCE(sw.area_id, aw.area_id) as area_id,
                COALESCE(sw.h3_index, aw.h3_index) as h3_index,
                COALESCE(sw.weight, aw.weight) as weight
            FROM bridge_area_h3_weight aw
            LEFT JOIN bridge_area_h3_weight_store sw
                ON sw.area_id = aw.area_id AND sw.h3_index = aw.h3_index
        ),
        """
    else:
        weight_cte = """
        weight_source AS (
            SELECT area_id, h3_index, weight
            FROM bridge_area_h3_weight
        ),
        """

    # Filter by area_type and select primary area (highest weight) for each H3
    # Each H3 belongs to exactly one "primary" commercial area
    # Display that area's total sales/flow/store without weight distribution
    sql = text(f"""
        WITH {weight_cte}
        hex_areas AS (
            SELECT ws.h3_index, ws.area_id, ws.weight, da.area_name, da.real_name
            FROM weight_source ws
            JOIN preset_area_scope pas ON pas.area_id = ws.area_id
            JOIN dim_area da ON da.area_id = ws.area_id
            WHERE da.area_type = :area_type
        ),
        primary_area AS (
            SELECT DISTINCT ON (h3_index) h3_index, area_id, area_name, real_name
            FROM hex_areas
            ORDER BY h3_index, weight DESC
        ),
        sales_agg AS (
            SELECT area_id, SUM(sales_amt) as sales_amt, SUM(sales_cnt) as sales_cnt
            FROM fact_sales_area_qtr
            WHERE qtr = :sales_qtr {cat_filter_sales.replace('s.', '')}
            GROUP BY area_id
        ),
        store_agg AS (
            SELECT area_id, SUM(store_cnt) as store_cnt, SUM(open_cnt) as open_cnt, SUM(close_cnt) as close_cnt
            FROM fact_store_area_qtr
            WHERE qtr = :store_qtr {cat_filter_store.replace('st.', '')}
            GROUP BY area_id
        )
        SELECT
            pa.h3_index,
            pa.area_id,
            pa.area_name,
            pa.real_name,
            COALESCE(s.sales_amt, 0) AS sales_amt,
            COALESCE(s.sales_cnt, 0)::int AS sales_cnt,
            COALESCE(f.flow_total, 0) AS flow_total,
            COALESCE(st.store_cnt, 0)::int AS store_cnt,
            COALESCE(st.open_cnt, 0)::int AS open_cnt,
            COALESCE(st.close_cnt, 0)::int AS close_cnt
        FROM primary_area pa
        LEFT JOIN sales_agg s ON s.area_id = pa.area_id
        LEFT JOIN fact_flow_area_qtr f ON f.area_id = pa.area_id AND f.qtr = :flow_qtr
        LEFT JOIN store_agg st ON st.area_id = pa.area_id
    """)

    rows = db.execute(sql, params).fetchall()

    data = []
    for r in rows:
        lat, lng = h3.cell_to_latlng(r.h3_index)
        data.append(
            HexagonSummary(
                h3_index=r.h3_index,
                lat=lat,
                lng=lng,
                area_id=r.area_id,
                area_name=r.area_name,
                real_name=r.real_name,
                sales_amt=r.sales_amt or 0,
                sales_cnt=r.sales_cnt or 0,
                flow_total=r.flow_total or 0,
                store_cnt=r.store_cnt or 0,
                open_cnt=r.open_cnt or 0,
                close_cnt=r.close_cnt or 0,
            )
        )

    return HexagonsResponse(
        data=data,
        data_asof=sales_qtr,
        area_type=area_type,
        weight_type=weight_type,
        filters={
            "category": category,
            "qtr_sales": sales_qtr,
            "qtr_flow": flow_qtr,
            "qtr_store": store_qtr,
        },
    )


# ---------------------------------------------------------------------------
# GET /api/map/hexagon/{h3_index}
# ---------------------------------------------------------------------------

@router.get("/hexagon/{h3_index}", response_model=HexagonDetailResponse)
def get_hexagon_detail(
    h3_index: str,
    area_type: str = Query("COMMERCIAL_AREA", regex="^(COMMERCIAL_AREA|ADMIN_DONG)$"),
    category: str | None = Query(None),
    qtr: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if not h3.is_valid_cell(h3_index):
        raise HTTPException(status_code=400, detail="Invalid H3 index")

    qtrs = _latest_quarters(db)
    sales_qtr = qtr or qtrs.get("sales", "")
    flow_qtr = qtr or qtrs.get("flow", "")
    store_qtr = qtr or qtrs.get("store", "")
    prev_sales_qtr = _prev_quarter(sales_qtr) if sales_qtr else ""
    prev_flow_qtr = _prev_quarter(flow_qtr) if flow_qtr else ""
    prev_store_qtr = _prev_quarter(store_qtr) if store_qtr else ""

    # Resolve area_ids from h3_index, filtered by area_type
    area_rows = db.execute(
        text("""
            SELECT bw.area_id, da.area_name, da.area_type, bw.weight
            FROM bridge_area_h3_weight bw
            JOIN dim_area da ON da.area_id = bw.area_id
            WHERE bw.h3_index = :h3 AND da.area_type = :area_type
        """),
        {"h3": h3_index, "area_type": area_type},
    ).fetchall()

    if not area_rows:
        raise HTTPException(status_code=404, detail="H3 index not found in scope")

    area_ids = [r.area_id for r in area_rows]
    area_names = [r.area_name for r in area_rows]
    weights = {r.area_id: float(r.weight) for r in area_rows}

    # Fetch fact data for current + previous quarter
    cat_filter = ""
    sales_params: dict = {
        "aids": tuple(area_ids),
        "qtr": sales_qtr,
        "prev_qtr": prev_sales_qtr,
    }
    if category:
        cat_filter = "AND cat_id = (SELECT cat_id FROM dim_category WHERE service_code = :cat)"
        sales_params["cat"] = category

    store_params: dict = {
        "aids": tuple(area_ids),
        "qtr": store_qtr,
        "prev_qtr": prev_store_qtr,
    }
    if category:
        store_params["cat"] = category

    # Sales
    sales_rows = db.execute(
        text(f"""
            SELECT area_id, qtr, sales_amt, sales_cnt
            FROM fact_sales_area_qtr
            WHERE area_id IN :aids AND qtr IN (:qtr, :prev_qtr) {cat_filter}
        """),
        sales_params,
    ).fetchall()

    # Flow
    flow_rows = db.execute(
        text("""
            SELECT area_id, qtr, flow_total, flow_by_hour, flow_by_weekday, flow_by_demo
            FROM fact_flow_area_qtr
            WHERE area_id IN :aids AND qtr IN (:qtr, :prev_qtr)
        """),
        {"aids": tuple(area_ids), "qtr": flow_qtr, "prev_qtr": prev_flow_qtr},
    ).fetchall()

    # Store
    store_rows = db.execute(
        text(f"""
            SELECT area_id, qtr, store_cnt, open_cnt, close_cnt
            FROM fact_store_area_qtr
            WHERE area_id IN :aids AND qtr IN (:qtr, :prev_qtr) {cat_filter}
        """),
        store_params,
    ).fetchall()

    # Aggregate with weights
    def _agg(rows, field: str, target_qtr: str) -> float | None:
        total = 0.0
        found = False
        for r in rows:
            if r.qtr == target_qtr:
                val = getattr(r, field, None)
                if val is not None:
                    total += float(val) * weights.get(r.area_id, 1)
                    found = True
        return round(total, 2) if found else None

    cur_sales = _agg(sales_rows, "sales_amt", sales_qtr)
    prev_sales = _agg(sales_rows, "sales_amt", prev_sales_qtr)
    cur_sales_cnt = _agg(sales_rows, "sales_cnt", sales_qtr)

    cur_flow = _agg(flow_rows, "flow_total", flow_qtr)
    prev_flow = _agg(flow_rows, "flow_total", prev_flow_qtr)

    cur_store = _agg(store_rows, "store_cnt", store_qtr)
    prev_store = _agg(store_rows, "store_cnt", prev_store_qtr)
    cur_open = _agg(store_rows, "open_cnt", store_qtr)
    cur_close = _agg(store_rows, "close_cnt", store_qtr)

    close_rate = round(cur_close / cur_store, 4) if cur_close and cur_store and cur_store > 0 else None
    comp_density = round(cur_store / len(area_ids), 2) if cur_store else None

    # Risk warnings
    warnings: list[str] = []
    if close_rate and close_rate > 0.15:
        warnings.append("폐업률 15% 초과")
    sales_growth = _safe_div(cur_sales, prev_sales)
    if sales_growth is not None and sales_growth < -0.1:
        warnings.append("매출 전분기 대비 10% 이상 감소")
    flow_growth = _safe_div(cur_flow, prev_flow)
    if flow_growth is not None and flow_growth < -0.1:
        warnings.append("유동인구 전분기 대비 10% 이상 감소")

    # Flow detail (merge from first available area — simplified)
    flow_by_hour = None
    flow_by_weekday = None
    flow_by_demo = None
    for r in flow_rows:
        if r.qtr == flow_qtr:
            flow_by_hour = flow_by_hour or r.flow_by_hour
            flow_by_weekday = flow_by_weekday or r.flow_by_weekday
            flow_by_demo = flow_by_demo or r.flow_by_demo

    lat, lng = h3.cell_to_latlng(h3_index)

    return HexagonDetailResponse(
        h3_index=h3_index,
        lat=lat,
        lng=lng,
        qtr=sales_qtr,
        data_asof=sales_qtr,
        areas=area_names,
        flow=FlowCard(
            flow_total=cur_flow,
            flow_by_hour=flow_by_hour,
            flow_by_weekday=flow_by_weekday,
            flow_by_demo=flow_by_demo,
        ),
        sales=SalesCard(
            sales_amt=cur_sales,
            sales_cnt=int(cur_sales_cnt) if cur_sales_cnt else None,
        ),
        competition=CompetitionCard(
            store_cnt=int(cur_store) if cur_store else None,
            open_cnt=int(cur_open) if cur_open else None,
            close_cnt=int(cur_close) if cur_close else None,
            close_rate=close_rate,
            competition_density=comp_density,
        ),
        growth=GrowthCard(
            sales_growth_rate=sales_growth,
            flow_growth_rate=flow_growth,
            store_growth_rate=_safe_div(cur_store, prev_store),
        ),
        risk=RiskCard(
            close_rate=close_rate,
            competition_density=comp_density,
            warnings=warnings,
        ),
    )


# ---------------------------------------------------------------------------
# GET /api/map/hexagons/heatmap — 시간대/요일별 유동인구 히트맵 (Phase 2 S2)
# ---------------------------------------------------------------------------

@router.get("/hexagons/heatmap", response_model=HeatmapResponse)
def get_hexagons_heatmap(
    area_type: str = Query("COMMERCIAL_AREA", regex="^(COMMERCIAL_AREA|ADMIN_DONG)$"),
    qtr: str | None = Query(None),
    mode: str = Query("hourly", regex="^(hourly|weekday)$"),
    db: Session = Depends(get_db),
):
    """Return time-based flow heatmap per hexagon."""
    qtrs = _latest_quarters(db)
    flow_qtr = qtr or qtrs.get("flow", "")

    sql = text("""
        SELECT DISTINCT ON (bw.h3_index)
            bw.h3_index, bw.area_id, da.area_name, da.real_name,
            f.flow_total, f.flow_by_hour, f.flow_by_weekday
        FROM bridge_area_h3_weight bw
        JOIN preset_area_scope pas ON pas.area_id = bw.area_id
        JOIN dim_area da ON da.area_id = bw.area_id
        LEFT JOIN fact_flow_area_qtr f ON f.area_id = bw.area_id AND f.qtr = :qtr
        WHERE da.area_type = :area_type
        ORDER BY bw.h3_index, bw.weight DESC
    """)

    rows = db.execute(sql, {"area_type": area_type, "qtr": flow_qtr}).fetchall()

    data = []
    for r in rows:
        lat, lng = h3.cell_to_latlng(r.h3_index)
        values: dict = {}
        if mode == "hourly" and r.flow_by_hour:
            values = r.flow_by_hour if isinstance(r.flow_by_hour, dict) else {}
        elif mode == "weekday" and r.flow_by_weekday:
            values = r.flow_by_weekday if isinstance(r.flow_by_weekday, dict) else {}
        data.append(HeatmapHexagon(
            h3_index=r.h3_index,
            lat=lat,
            lng=lng,
            area_name=r.area_name,
            real_name=r.real_name,
            flow_total=r.flow_total,
            values=values,
        ))

    return HeatmapResponse(data=data, data_asof=flow_qtr, mode=mode)


# ---------------------------------------------------------------------------
# GET /api/map/hexagon/{h3_index}/peaktime — 피크타임 분석 (Phase 2 S2)
# ---------------------------------------------------------------------------

@router.get("/hexagon/{h3_index}/peaktime", response_model=PeaktimeAnalysis)
def get_peaktime(
    h3_index: str,
    area_type: str = Query("COMMERCIAL_AREA", regex="^(COMMERCIAL_AREA|ADMIN_DONG)$"),
    qtr: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Analyze peak/off-peak hours for a hexagon."""
    if not h3.is_valid_cell(h3_index):
        raise HTTPException(status_code=400, detail="Invalid H3 index")

    qtrs = _latest_quarters(db)
    flow_qtr = qtr or qtrs.get("flow", "")

    rows = db.execute(text("""
        SELECT f.flow_by_hour, f.flow_by_weekday, f.flow_by_demo, f.flow_total
        FROM bridge_area_h3_weight bw
        JOIN dim_area da ON da.area_id = bw.area_id
        JOIN fact_flow_area_qtr f ON f.area_id = bw.area_id AND f.qtr = :qtr
        WHERE bw.h3_index = :h3 AND da.area_type = :area_type
        ORDER BY bw.weight DESC
        LIMIT 1
    """), {"h3": h3_index, "qtr": flow_qtr, "area_type": area_type}).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No flow data for this hexagon")

    r = rows[0]
    hourly = r.flow_by_hour if isinstance(r.flow_by_hour, dict) else {}
    weekday = r.flow_by_weekday if isinstance(r.flow_by_weekday, dict) else {}
    demo = r.flow_by_demo if isinstance(r.flow_by_demo, dict) else {}

    # Find peak and off-peak hours
    sorted_hours = sorted(hourly.items(), key=lambda x: int(x[1]) if x[1] else 0, reverse=True)
    peak_hours = [int(h) for h, _ in sorted_hours[:3]] if sorted_hours else []
    off_peak_hours = [int(h) for h, _ in sorted_hours[-3:]] if len(sorted_hours) >= 3 else []

    return PeaktimeAnalysis(
        h3_index=h3_index,
        qtr=flow_qtr,
        flow_total=r.flow_total,
        peak_hours=peak_hours,
        off_peak_hours=off_peak_hours,
        hourly_pattern=hourly,
        weekday_pattern=weekday,
        demo_breakdown=demo,
    )


# ---------------------------------------------------------------------------
# GET /api/map/hexagons/risk — 리스크 레이어 (Phase 2 S5)
# ---------------------------------------------------------------------------

@router.get("/hexagons/risk", response_model=RiskLayerResponse)
def get_risk_layer(
    area_type: str = Query("COMMERCIAL_AREA", regex="^(COMMERCIAL_AREA|ADMIN_DONG)$"),
    category: str | None = Query(None),
    qtr: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Return risk score per hexagon for the risk layer."""
    qtrs = _latest_quarters(db)
    sales_qtr = qtr or qtrs.get("sales", "")
    store_qtr = qtr or qtrs.get("store", "")
    flow_qtr = qtr or qtrs.get("flow", "")
    prev_sales_qtr = _prev_quarter(sales_qtr) if sales_qtr else ""
    prev_store_qtr = _prev_quarter(store_qtr) if store_qtr else ""
    prev_flow_qtr = _prev_quarter(flow_qtr) if flow_qtr else ""

    cat_filter = ""
    params: dict = {
        "area_type": area_type,
        "sales_qtr": sales_qtr,
        "prev_sales_qtr": prev_sales_qtr,
        "store_qtr": store_qtr,
        "prev_store_qtr": prev_store_qtr,
        "flow_qtr": flow_qtr,
        "prev_flow_qtr": prev_flow_qtr,
    }
    if category:
        cat_filter = "AND cat_id = (SELECT cat_id FROM dim_category WHERE service_code = :cat)"
        params["cat"] = category

    # Fetch per-area metrics for current and previous quarter
    area_sql = text(f"""
        WITH areas AS (
            SELECT DISTINCT ON (bw.h3_index)
                bw.h3_index, bw.area_id, da.area_name, da.real_name
            FROM bridge_area_h3_weight bw
            JOIN preset_area_scope pas ON pas.area_id = bw.area_id
            JOIN dim_area da ON da.area_id = bw.area_id
            WHERE da.area_type = :area_type
            ORDER BY bw.h3_index, bw.weight DESC
        )
        SELECT
            a.h3_index, a.area_id, a.area_name, a.real_name,
            cur_s.sales_amt AS cur_sales, prev_s.sales_amt AS prev_sales,
            cur_st.store_cnt AS cur_store, prev_st.store_cnt AS prev_store,
            cur_st.close_cnt, cur_st.open_cnt,
            cur_f.flow_total AS cur_flow, prev_f.flow_total AS prev_flow
        FROM areas a
        LEFT JOIN (SELECT area_id, SUM(sales_amt) AS sales_amt FROM fact_sales_area_qtr WHERE qtr = :sales_qtr {cat_filter} GROUP BY area_id) cur_s ON cur_s.area_id = a.area_id
        LEFT JOIN (SELECT area_id, SUM(sales_amt) AS sales_amt FROM fact_sales_area_qtr WHERE qtr = :prev_sales_qtr {cat_filter} GROUP BY area_id) prev_s ON prev_s.area_id = a.area_id
        LEFT JOIN (SELECT area_id, SUM(store_cnt) AS store_cnt, SUM(close_cnt) AS close_cnt, SUM(open_cnt) AS open_cnt FROM fact_store_area_qtr WHERE qtr = :store_qtr {cat_filter} GROUP BY area_id) cur_st ON cur_st.area_id = a.area_id
        LEFT JOIN (SELECT area_id, SUM(store_cnt) AS store_cnt FROM fact_store_area_qtr WHERE qtr = :prev_store_qtr {cat_filter} GROUP BY area_id) prev_st ON prev_st.area_id = a.area_id
        LEFT JOIN fact_flow_area_qtr cur_f ON cur_f.area_id = a.area_id AND cur_f.qtr = :flow_qtr
        LEFT JOIN fact_flow_area_qtr prev_f ON prev_f.area_id = a.area_id AND prev_f.qtr = :prev_flow_qtr
    """)

    rows = db.execute(area_sql, params).fetchall()

    data = []
    for r in rows:
        lat, lng = h3.cell_to_latlng(r.h3_index)
        close_qoq = _safe_div(float(r.close_cnt) if r.close_cnt else None,
                              float(r.open_cnt) if r.open_cnt else None) if r.close_cnt and r.open_cnt else None
        sales_qoq = _safe_div(float(r.cur_sales) if r.cur_sales else None,
                              float(r.prev_sales) if r.prev_sales else None)
        store_growth = _safe_div(float(r.cur_store) if r.cur_store else None,
                                 float(r.prev_store) if r.prev_store else None)
        flow_qoq = _safe_div(float(r.cur_flow) if r.cur_flow else None,
                             float(r.prev_flow) if r.prev_flow else None)

        close_rate = (float(r.close_cnt) / float(r.cur_store)) if r.close_cnt and r.cur_store and float(r.cur_store) > 0 else 0.0

        # Risk score: higher = more risk
        # w1*폐업률 + w2*점포증가율 + w3*매출감소 + w4*유동감소
        risk_score = 0.0
        risk_factors = []

        if close_rate > 0:
            risk_score += 0.3 * min(close_rate / 0.2, 1.0)
            if close_rate > 0.1:
                risk_factors.append(f"폐업률 {close_rate*100:.1f}%")

        if store_growth is not None and store_growth > 0.1:
            risk_score += 0.2 * min(store_growth / 0.3, 1.0)
            risk_factors.append(f"점포 증가율 +{store_growth*100:.1f}% (경쟁 과밀)")

        if sales_qoq is not None and sales_qoq < 0:
            risk_score += 0.3 * min(abs(sales_qoq) / 0.2, 1.0)
            if sales_qoq < -0.05:
                risk_factors.append(f"매출 QoQ {sales_qoq*100:.1f}%")

        if flow_qoq is not None and flow_qoq < 0:
            risk_score += 0.2 * min(abs(flow_qoq) / 0.2, 1.0)
            if flow_qoq < -0.05:
                risk_factors.append(f"유동인구 QoQ {flow_qoq*100:.1f}%")

        data.append(RiskHexagon(
            h3_index=r.h3_index,
            lat=lat,
            lng=lng,
            area_name=r.area_name,
            real_name=r.real_name,
            risk_score=round(risk_score, 4),
            risk_factors=risk_factors,
            close_rate=round(close_rate, 4),
            sales_qoq=sales_qoq,
            store_growth=store_growth,
            flow_qoq=flow_qoq,
            sales_amt=float(r.cur_sales) if r.cur_sales else None,
        ))

    return RiskLayerResponse(data=data, data_asof=sales_qtr)


# ---------------------------------------------------------------------------
# GET /api/map/hexagon/{h3_index}/risk — 리스크 분해 (Phase 2 S5)
# ---------------------------------------------------------------------------

@router.get("/hexagon/{h3_index}/risk", response_model=RiskAnalysis)
def get_risk_analysis(
    h3_index: str,
    area_type: str = Query("COMMERCIAL_AREA", regex="^(COMMERCIAL_AREA|ADMIN_DONG)$"),
    category: str | None = Query(None),
    qtr: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Decompose risk factors for a specific hexagon and suggest alternatives."""
    if not h3.is_valid_cell(h3_index):
        raise HTTPException(status_code=400, detail="Invalid H3 index")

    # Get risk data for all hexagons to find alternatives
    risk_response = get_risk_layer(area_type=area_type, category=category, qtr=qtr, db=db)

    target = None
    others = []
    for hex_risk in risk_response.data:
        if hex_risk.h3_index == h3_index:
            target = hex_risk
        else:
            others.append(hex_risk)

    if not target:
        raise HTTPException(status_code=404, detail="H3 index not found in risk layer")

    # Find alternative areas: low risk + decent sales
    low_risk_alternatives = sorted(
        [h for h in others if h.sales_amt and h.sales_amt > 0],
        key=lambda x: (x.risk_score, -(x.sales_amt or 0)),
    )[:2]

    return RiskAnalysis(
        h3_index=h3_index,
        area_name=target.area_name,
        real_name=target.real_name,
        risk_score=target.risk_score,
        risk_factors=target.risk_factors,
        close_rate=target.close_rate,
        sales_qoq=target.sales_qoq,
        store_growth=target.store_growth,
        flow_qoq=target.flow_qoq,
        alternative_areas=[
            {
                "h3_index": alt.h3_index,
                "area_name": alt.area_name,
                "real_name": alt.real_name,
                "risk_score": alt.risk_score,
                "sales_amt": alt.sales_amt,
            }
            for alt in low_risk_alternatives
        ],
        data_asof=risk_response.data_asof,
    )


# ---------------------------------------------------------------------------
# GET /api/map/hexagon/{h3_index}/compare — 분기 비교 (Phase 3 S4)
# ---------------------------------------------------------------------------

@router.get("/hexagon/{h3_index}/compare", response_model=CompareResponse)
def get_quarter_comparison(
    h3_index: str,
    qtr1: str = Query(..., description="First quarter (e.g. 20243)"),
    qtr2: str = Query(..., description="Second quarter (e.g. 20244)"),
    area_type: str = Query("COMMERCIAL_AREA", regex="^(COMMERCIAL_AREA|ADMIN_DONG)$"),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Compare metrics between two quarters for a specific hexagon."""
    if not h3.is_valid_cell(h3_index):
        raise HTTPException(status_code=400, detail="Invalid H3 index")

    area_rows = db.execute(text("""
        SELECT bw.area_id, da.area_name, bw.weight
        FROM bridge_area_h3_weight bw
        JOIN dim_area da ON da.area_id = bw.area_id
        WHERE bw.h3_index = :h3 AND da.area_type = :area_type
    """), {"h3": h3_index, "area_type": area_type}).fetchall()

    if not area_rows:
        raise HTTPException(status_code=404, detail="H3 index not found")

    area_ids = tuple(r.area_id for r in area_rows)
    weights = {r.area_id: float(r.weight) for r in area_rows}

    cat_filter = ""
    params: dict = {"aids": area_ids, "qtr1": qtr1, "qtr2": qtr2}
    if category:
        cat_filter = "AND cat_id = (SELECT cat_id FROM dim_category WHERE service_code = :cat)"
        params["cat"] = category

    # Sales comparison
    sales_rows = db.execute(text(f"""
        SELECT area_id, qtr, SUM(sales_amt) AS sales_amt, SUM(sales_cnt) AS sales_cnt
        FROM fact_sales_area_qtr
        WHERE area_id IN :aids AND qtr IN (:qtr1, :qtr2) {cat_filter}
        GROUP BY area_id, qtr
    """), params).fetchall()

    # Flow comparison
    flow_rows = db.execute(text("""
        SELECT area_id, qtr, flow_total, flow_by_hour, flow_by_weekday
        FROM fact_flow_area_qtr
        WHERE area_id IN :aids AND qtr IN (:qtr1, :qtr2)
    """), {"aids": area_ids, "qtr1": qtr1, "qtr2": qtr2}).fetchall()

    # Store comparison
    store_rows = db.execute(text(f"""
        SELECT area_id, qtr, SUM(store_cnt) AS store_cnt, SUM(close_cnt) AS close_cnt
        FROM fact_store_area_qtr
        WHERE area_id IN :aids AND qtr IN (:qtr1, :qtr2) {cat_filter}
        GROUP BY area_id, qtr
    """), params).fetchall()

    # Also get the average change across all areas for relative comparison
    avg_sales = db.execute(text(f"""
        SELECT qtr, AVG(sales_amt) AS avg_sales
        FROM fact_sales_area_qtr
        WHERE area_id IN (SELECT area_id FROM preset_area_scope)
          AND qtr IN (:qtr1, :qtr2) {cat_filter}
        GROUP BY qtr
    """), params).fetchall()
    avg_sales_map = {r.qtr: float(r.avg_sales) if r.avg_sales else None for r in avg_sales}

    def _weighted_sum(rows, field, target_qtr):
        total = 0.0
        found = False
        for r in rows:
            if r.qtr == target_qtr:
                val = getattr(r, field, None)
                if val is not None:
                    total += float(val) * weights.get(r.area_id, 1)
                    found = True
        return round(total, 2) if found else None

    comparisons = []
    for metric_name, rows_data, field in [
        ("매출", sales_rows, "sales_amt"),
        ("유동인구", flow_rows, "flow_total"),
        ("점포수", store_rows, "store_cnt"),
    ]:
        v1 = _weighted_sum(rows_data, field, qtr1)
        v2 = _weighted_sum(rows_data, field, qtr2)
        change_rate = _safe_div(v2, v1)
        avg_change = _safe_div(avg_sales_map.get(qtr2), avg_sales_map.get(qtr1)) if metric_name == "매출" else None

        comparisons.append(QuarterComparison(
            metric=metric_name,
            qtr1_value=v1,
            qtr2_value=v2,
            change_rate=change_rate,
            avg_change_rate=avg_change,
            above_avg=(change_rate > avg_change) if change_rate is not None and avg_change is not None else None,
        ))

    # Hourly change detail
    hourly_q1 = {}
    hourly_q2 = {}
    for r in flow_rows:
        if r.flow_by_hour and isinstance(r.flow_by_hour, dict):
            target = hourly_q1 if r.qtr == qtr1 else hourly_q2
            for k, v in r.flow_by_hour.items():
                target[k] = target.get(k, 0) + (int(v) if v else 0)

    return CompareResponse(
        h3_index=h3_index,
        qtr1=qtr1,
        qtr2=qtr2,
        comparisons=comparisons,
        hourly_q1=hourly_q1 if hourly_q1 else None,
        hourly_q2=hourly_q2 if hourly_q2 else None,
        data_asof=qtr2,
    )
