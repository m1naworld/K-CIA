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
    RecommendationCard,
    RiskCard,
    SalesCard,
    TrendData,
    TrendPoint,
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
    prev_sales_qtr = _prev_quarter(sales_qtr) if sales_qtr else ""

    cat_filter_sales = ""
    cat_filter_store = ""
    cat_filter_prev = ""
    params: dict = {
        "area_type": area_type,
        "sales_qtr": sales_qtr,
        "prev_sales_qtr": prev_sales_qtr,
        "flow_qtr": flow_qtr,
        "store_qtr": store_qtr,
    }
    if category:
        cat_filter_sales = "AND s.cat_id = (SELECT cat_id FROM dim_category WHERE service_code = :cat)"
        cat_filter_store = "AND st.cat_id = (SELECT cat_id FROM dim_category WHERE service_code = :cat)"
        cat_filter_prev = "AND cat_id = (SELECT cat_id FROM dim_category WHERE service_code = :cat)"
        params["cat"] = category

    # Select weight table based on weight_type parameter
    if weight_type == "store":
        weight_cte = """
        weight_source AS (
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
        prev_sales_agg AS (
            SELECT area_id, SUM(sales_amt) as sales_amt
            FROM fact_sales_area_qtr
            WHERE qtr = :prev_sales_qtr {cat_filter_prev}
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
            COALESCE(st.close_cnt, 0)::int AS close_cnt,
            ps.sales_amt AS prev_sales_amt
        FROM primary_area pa
        LEFT JOIN sales_agg s ON s.area_id = pa.area_id
        LEFT JOIN prev_sales_agg ps ON ps.area_id = pa.area_id
        LEFT JOIN fact_flow_area_qtr f ON f.area_id = pa.area_id AND f.qtr = :flow_qtr
        LEFT JOIN store_agg st ON st.area_id = pa.area_id
    """)

    rows = db.execute(sql, params).fetchall()

    data = []
    for r in rows:
        lat, lng = h3.h3_to_geo(r.h3_index)
        cur = float(r.sales_amt) if r.sales_amt else None
        prev = float(r.prev_sales_amt) if r.prev_sales_amt else None
        sales_qoq = _safe_div(cur, prev)
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
                sales_qoq=sales_qoq,
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
# Recommendation & Trend helpers
# ---------------------------------------------------------------------------

def _build_recommendation(
    *,
    sales_growth: float | None,
    flow_growth: float | None,
    store_growth: float | None,
    close_rate: float | None,
    comp_density: float | None,
    cur_flow: float | None,
    cur_sales: float | None,
) -> RecommendationCard:
    """Compute suitability score (0-100) from metrics."""
    score = 50  # baseline
    pros: list[str] = []
    cons: list[str] = []

    # Sales growth (max ±20 pts)
    if sales_growth is not None:
        if sales_growth > 0.05:
            score += 15
            pros.append(f"매출 성장 중 (+{sales_growth * 100:.1f}%)")
        elif sales_growth > 0:
            score += 8
            pros.append(f"매출 소폭 상승 (+{sales_growth * 100:.1f}%)")
        elif sales_growth > -0.05:
            score -= 5
        else:
            score -= 15
            cons.append(f"매출 감소 추세 ({sales_growth * 100:.1f}%)")

    # Flow growth (max ±15 pts)
    if flow_growth is not None:
        if flow_growth > 0.05:
            score += 12
            pros.append(f"유동인구 증가 (+{flow_growth * 100:.1f}%)")
        elif flow_growth > 0:
            score += 5
        elif flow_growth > -0.05:
            score -= 3
        else:
            score -= 12
            cons.append(f"유동인구 감소 ({flow_growth * 100:.1f}%)")

    # Close rate (max ±15 pts)
    if close_rate is not None:
        if close_rate < 0.05:
            score += 10
            pros.append("낮은 폐업률 (안정적 상권)")
        elif close_rate < 0.10:
            score += 3
        elif close_rate < 0.15:
            score -= 5
        else:
            score -= 15
            cons.append(f"높은 폐업률 ({close_rate * 100:.1f}%)")

    # Competition density
    if comp_density is not None:
        if comp_density > 50:
            cons.append(f"경쟁 밀집 지역 (점포 {comp_density:.0f}개)")
            score -= 8
        elif comp_density < 10:
            pros.append("경쟁 여유 공간")
            score += 5

    # Flow volume bonus
    if cur_flow and cur_flow > 500000:
        score += 5
        if f"유동인구 증가" not in " ".join(pros):
            pros.append("높은 유동인구 기반")

    score = max(0, min(100, score))

    if score >= 80:
        grade = "S"
    elif score >= 65:
        grade = "A"
    elif score >= 50:
        grade = "B"
    elif score >= 35:
        grade = "C"
    else:
        grade = "D"

    grade_labels = {"S": "적극 추천", "A": "추천", "B": "보통", "C": "주의", "D": "비추천"}
    summary = f"{grade_labels[grade]} (점수 {score}/100)"

    return RecommendationCard(
        score=score,
        grade=grade,
        pros=pros[:4],
        cons=cons[:4],
        summary=summary,
    )


def _build_trend(
    db: Session,
    area_ids: list[int],
    weights: dict[int, float],
    current_qtr: str,
    category: str | None,
) -> TrendData:
    """Fetch last 4 quarters of data for trend mini charts."""
    # Generate last 4 quarter strings
    qtrs = []
    q = current_qtr
    for _ in range(4):
        qtrs.append(q)
        q = _prev_quarter(q)
    qtrs.reverse()  # oldest first

    cat_filter = ""
    params: dict = {"aids": tuple(area_ids), "qtrs": tuple(qtrs)}
    if category:
        cat_filter = "AND cat_id = (SELECT cat_id FROM dim_category WHERE service_code = :cat)"
        params["cat"] = category

    # Sales trend
    sales_rows = db.execute(
        text(f"""
            SELECT qtr, SUM(sales_amt) as sales_amt
            FROM fact_sales_area_qtr
            WHERE area_id IN :aids AND qtr IN :qtrs {cat_filter}
            GROUP BY qtr ORDER BY qtr
        """),
        params,
    ).fetchall()
    sales_map = {r.qtr: float(r.sales_amt) for r in sales_rows}

    # Flow trend
    flow_rows = db.execute(
        text("""
            SELECT qtr, SUM(flow_total) as flow_total
            FROM fact_flow_area_qtr
            WHERE area_id IN :aids AND qtr IN :qtrs
            GROUP BY qtr ORDER BY qtr
        """),
        {"aids": tuple(area_ids), "qtrs": tuple(qtrs)},
    ).fetchall()
    flow_map = {r.qtr: float(r.flow_total) for r in flow_rows}

    # Store trend
    store_rows = db.execute(
        text(f"""
            SELECT qtr, SUM(store_cnt) as store_cnt
            FROM fact_store_area_qtr
            WHERE area_id IN :aids AND qtr IN :qtrs {cat_filter}
            GROUP BY qtr ORDER BY qtr
        """),
        params,
    ).fetchall()
    store_map = {r.qtr: float(r.store_cnt) for r in store_rows}

    def _fmt_qtr(q: str) -> str:
        """'20241' → '24Q1'"""
        return f"{q[2:4]}Q{q[-1]}"

    return TrendData(
        sales=[TrendPoint(qtr=_fmt_qtr(q), value=sales_map.get(q)) for q in qtrs],
        flow=[TrendPoint(qtr=_fmt_qtr(q), value=flow_map.get(q)) for q in qtrs],
        store=[TrendPoint(qtr=_fmt_qtr(q), value=store_map.get(q)) for q in qtrs],
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

    # --- Recommendation Card ---
    rec = _build_recommendation(
        sales_growth=sales_growth,
        flow_growth=flow_growth,
        store_growth=_safe_div(cur_store, prev_store),
        close_rate=close_rate,
        comp_density=comp_density,
        cur_flow=cur_flow,
        cur_sales=cur_sales,
    )

    # --- Trend Data (last 4 quarters) ---
    trend = _build_trend(db, area_ids, weights, sales_qtr, category)

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
        recommendation=rec,
        trend=trend,
    )
