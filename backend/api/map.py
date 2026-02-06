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
        lat, lng = h3.h3_to_geo(r.h3_index)
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
    if not h3.h3_is_valid(h3_index):
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

    lat, lng = h3.h3_to_geo(h3_index)

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
