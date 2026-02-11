"""Map API endpoints: hexagon grid and hexagon detail."""

from __future__ import annotations

import json

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

import h3

from db import get_db
from api.schemas import (
    ComparisonBreakdown,
    ComparisonChange,
    ComparisonMetricSnapshot,
    ComparisonRequest,
    ComparisonResponse,
    CompetitionCard,
    DemoAgeItem,
    DemoCard,
    DemoGenderRatio,
    FacilityCard,
    FacilityItem,
    FlowCard,
    GrowthCard,
    HexagonDetailResponse,
    HexagonSummary,
    HexagonsResponse,
    RecommendationCard,
    RiskCard,
    SalesCard,
    TimeSlotItem,
    TimeSlotRecommendation,
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


FACILITY_LABELS: dict[str, str] = {
    "VIATR_FCLTY": "관광시설",
    "PBLOFC": "관공서",
    "BANK": "은행",
    "GEHSPT": "종합병원",
    "GNRL_HSPTL": "일반병원",
    "PARMACY": "약국",
    "KNDRGR": "유치원",
    "ELESCH": "초등학교",
    "MSKUL": "중학교",
    "HGSCHL": "고등학교",
    "UNIV": "대학교",
    "DRTS": "백화점",
    "SUPMK": "대형마트",
    "THEAT": "극장",
    "STAYNG_FCLTY": "숙박시설",
    "ARPRT": "공항",
    "RLROAD_STATN": "철도역",
    "BUS_TRMINL": "버스터미널",
    "SUBWAY_STATN": "지하철역",
    "BUS_STTN": "버스정류장",
}

WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]
AGE_GROUPS = ["10", "20", "30", "40", "50", "60+"]


def _build_facility_card(
    db: Session, area_ids: list[int], qtr: str
) -> FacilityCard | None:
    """Build FacilityCard from fact_facility_area_qtr."""
    rows = db.execute(
        text("""
            SELECT facility_type, SUM(facility_cnt) AS cnt
            FROM fact_facility_area_qtr
            WHERE area_id IN :aids AND qtr = :qtr
            GROUP BY facility_type
            ORDER BY cnt DESC
        """),
        {"aids": tuple(area_ids), "qtr": qtr},
    ).fetchall()

    if not rows:
        return None

    items = [
        FacilityItem(
            facility_type=r.facility_type,
            label=FACILITY_LABELS.get(r.facility_type, r.facility_type),
            count=int(r.cnt),
        )
        for r in rows
        if int(r.cnt) > 0
    ]
    total = sum(i.count for i in items)
    top_types = [i.label for i in items[:5]]

    return FacilityCard(total_count=total, facilities=items, top_types=top_types)


def _build_demo_card(flow_by_demo: dict | str | None, flow_total: float | None) -> DemoCard | None:
    """Build DemoCard from flow_by_demo JSONB."""
    if not flow_by_demo:
        return None

    demo = flow_by_demo
    if isinstance(demo, str):
        demo = json.loads(demo)
    if not isinstance(demo, dict):
        return None

    total = float(flow_total) if flow_total else 0
    if total <= 0:
        return None

    # Gender ratio
    male_cnt = float(demo.get("male", 0))
    female_cnt = float(demo.get("female", 0))
    gender_total = male_cnt + female_cnt
    gender = DemoGenderRatio(
        male=round(male_cnt / gender_total, 4) if gender_total > 0 else None,
        female=round(female_cnt / gender_total, 4) if gender_total > 0 else None,
    )
    peak_gender = "남성" if male_cnt >= female_cnt else "여성"

    # Age distribution
    age_items: list[DemoAgeItem] = []
    age_keys = [
        ("age_10", "10"), ("age_20", "20"), ("age_30", "30"),
        ("age_40", "40"), ("age_50", "50"), ("age_60+", "60+"),
    ]
    age_total = sum(float(demo.get(k, 0)) for k, _ in age_keys)
    peak_age = ("", 0.0)
    for key, label in age_keys:
        cnt = float(demo.get(key, 0))
        ratio = round(cnt / age_total, 4) if age_total > 0 else 0
        age_items.append(DemoAgeItem(age_group=label, ratio=ratio, count=cnt))
        if cnt > peak_age[1]:
            peak_age = (label, cnt)

    return DemoCard(
        gender=gender,
        age_distribution=age_items,
        peak_age_group=peak_age[0] if peak_age[0] else None,
        peak_gender=peak_gender,
    )


def _build_time_slot(
    flow_by_hour: dict | str | None,
    flow_by_weekday: dict | str | None,
) -> TimeSlotRecommendation | None:
    """Build TimeSlotRecommendation from flow_by_hour/weekday JSONB.

    flow_by_hour keys: "00_06", "06_11", "11_14", "14_17", "17_21", "21_24"
    flow_by_weekday keys: "mon"~"sun"
    """
    # Parse weekday data
    wd_map = {
        "mon": "월", "tue": "화", "wed": "수", "thu": "목",
        "fri": "금", "sat": "토", "sun": "일",
    }
    peak_weekday = None
    if flow_by_weekday:
        wd_data = flow_by_weekday
        if isinstance(wd_data, str):
            wd_data = json.loads(wd_data)
        if isinstance(wd_data, dict):
            wd_values: list[tuple[str, float]] = []
            for k, v in wd_data.items():
                try:
                    if v is not None:
                        wd_values.append((k, float(v)))
                except (ValueError, TypeError):
                    continue
            if wd_values:
                best_wd = max(wd_values, key=lambda x: x[1])
                peak_weekday = wd_map.get(best_wd[0].lower(), best_wd[0])

    # Parse hourly range data (keys: "00_06", "06_11", "11_14", "14_17", "17_21", "21_24")
    slot_defs = [
        ("00_06", "00~06", "심야·새벽"),
        ("06_11", "06~11", "오전"),
        ("11_14", "11~14", "점심"),
        ("14_17", "14~17", "오후"),
        ("17_21", "17~21", "저녁"),
        ("21_24", "21~24", "야간"),
    ]

    recommendations: list[TimeSlotItem] = []
    peak_hours: list[int] = []
    off_peak_hours: list[int] = []

    if flow_by_hour:
        hour_data = flow_by_hour
        if isinstance(hour_data, str):
            hour_data = json.loads(hour_data)
        if isinstance(hour_data, dict):
            slot_flows: list[tuple[str, str, str, float]] = []
            for key, label, desc in slot_defs:
                val = hour_data.get(key)
                if val is not None:
                    try:
                        slot_flows.append((key, label, desc, float(val)))
                    except (ValueError, TypeError):
                        pass

            total_flow = sum(f for _, _, _, f in slot_flows)
            if total_flow > 0:
                for key, label, desc, flow in slot_flows:
                    ratio = round(flow / total_flow, 4)
                    recommendations.append(TimeSlotItem(hour_range=label, label=desc, flow_ratio=ratio))

                # Sort by flow descending for peak/off-peak
                sorted_slots = sorted(slot_flows, key=lambda x: x[3], reverse=True)
                # Peak: midpoint hour of top 2 slots
                for key, _, _, _ in sorted_slots[:2]:
                    parts = key.split("_")
                    mid = (int(parts[0]) + int(parts[1])) // 2
                    peak_hours.append(mid)
                # Off-peak: midpoint of bottom slot
                for key, _, _, _ in sorted_slots[-1:]:
                    parts = key.split("_")
                    mid = (int(parts[0]) + int(parts[1])) // 2
                    off_peak_hours.append(mid)

    # If no hourly data, still return weekday info if available
    if not recommendations and not peak_weekday:
        return None

    return TimeSlotRecommendation(
        peak_hours=peak_hours,
        peak_weekday=peak_weekday,
        off_peak_hours=off_peak_hours,
        recommendations=recommendations,
    )


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

    # --- Facility Card (M6-4) ---
    # Use the latest facility quarter available for these areas
    fac_qtr_row = db.execute(
        text("""
            SELECT MAX(qtr) FROM fact_facility_area_qtr WHERE area_id IN :aids
        """),
        {"aids": tuple(area_ids)},
    ).scalar()
    facility_card = _build_facility_card(db, area_ids, fac_qtr_row) if fac_qtr_row else None

    # --- Demo Card (M6-4) ---
    demo_card = _build_demo_card(flow_by_demo, cur_flow)

    # --- Time Slot Recommendation (M6-4) ---
    time_slot_card = _build_time_slot(flow_by_hour, flow_by_weekday)

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
        facility=facility_card,
        demo=demo_card,
        time_slot=time_slot_card,
    )


# ---------------------------------------------------------------------------
# POST /api/map/compare
# ---------------------------------------------------------------------------

@router.post("/compare", response_model=ComparisonResponse)
def compare_quarters(
    req: ComparisonRequest = Body(...),
    db: Session = Depends(get_db),
):
    """Compare two quarters for a given H3 hexagon."""
    # Validate H3
    if not h3.h3_is_valid(req.h3_index):
        raise HTTPException(status_code=400, detail="Invalid H3 index")

    if req.qtr_before == req.qtr_after:
        raise HTTPException(status_code=400, detail="qtr_before and qtr_after must differ")

    # Resolve area_ids from h3_index
    area_rows = db.execute(
        text("""
            SELECT bw.area_id, da.area_name, bw.weight
            FROM bridge_area_h3_weight bw
            JOIN dim_area da ON da.area_id = bw.area_id
            WHERE bw.h3_index = :h3 AND da.area_type = :area_type
        """),
        {"h3": req.h3_index, "area_type": req.area_type},
    ).fetchall()

    if not area_rows:
        raise HTTPException(status_code=404, detail="H3 index not found in scope")

    area_ids = [r.area_id for r in area_rows]
    area_names = [r.area_name for r in area_rows]
    weights = {r.area_id: float(r.weight) for r in area_rows}

    # Category filter
    cat_filter = ""
    params: dict = {
        "aids": tuple(area_ids),
        "qtr_b": req.qtr_before,
        "qtr_a": req.qtr_after,
    }
    if req.category:
        cat_filter = "AND cat_id = (SELECT cat_id FROM dim_category WHERE service_code = :cat)"
        params["cat"] = req.category

    # Fetch sales for both quarters
    sales_rows = db.execute(
        text(f"""
            SELECT area_id, qtr, SUM(sales_amt) AS sales_amt, SUM(sales_cnt) AS sales_cnt
            FROM fact_sales_area_qtr
            WHERE area_id IN :aids AND qtr IN (:qtr_b, :qtr_a) {cat_filter}
            GROUP BY area_id, qtr
        """),
        params,
    ).fetchall()

    # Fetch flow for both quarters
    flow_rows = db.execute(
        text("""
            SELECT area_id, qtr, flow_total, flow_by_hour, flow_by_weekday, flow_by_demo
            FROM fact_flow_area_qtr
            WHERE area_id IN :aids AND qtr IN (:qtr_b, :qtr_a)
        """),
        {"aids": tuple(area_ids), "qtr_b": req.qtr_before, "qtr_a": req.qtr_after},
    ).fetchall()

    # Fetch store for both quarters
    store_rows = db.execute(
        text(f"""
            SELECT area_id, qtr, SUM(store_cnt) AS store_cnt,
                   SUM(open_cnt) AS open_cnt, SUM(close_cnt) AS close_cnt
            FROM fact_store_area_qtr
            WHERE area_id IN :aids AND qtr IN (:qtr_b, :qtr_a) {cat_filter}
            GROUP BY area_id, qtr
        """),
        params,
    ).fetchall()

    # Weight-based aggregation helper
    def _wagg(rows: list, field: str, target_qtr: str) -> float | None:
        total = 0.0
        found = False
        for r in rows:
            if r.qtr == target_qtr:
                val = getattr(r, field, None)
                if val is not None:
                    total += float(val) * weights.get(r.area_id, 1)
                    found = True
        return round(total, 2) if found else None

    # Build before snapshot
    b_sales = _wagg(sales_rows, "sales_amt", req.qtr_before)
    b_sales_cnt = _wagg(sales_rows, "sales_cnt", req.qtr_before)
    b_flow = _wagg(flow_rows, "flow_total", req.qtr_before)
    b_store = _wagg(store_rows, "store_cnt", req.qtr_before)
    b_open = _wagg(store_rows, "open_cnt", req.qtr_before)
    b_close = _wagg(store_rows, "close_cnt", req.qtr_before)
    b_close_rate = round(b_close / b_store, 4) if b_close and b_store and b_store > 0 else None

    before = ComparisonMetricSnapshot(
        sales_amt=b_sales,
        sales_cnt=int(b_sales_cnt) if b_sales_cnt else None,
        flow_total=b_flow,
        store_cnt=int(b_store) if b_store else None,
        open_cnt=int(b_open) if b_open else None,
        close_cnt=int(b_close) if b_close else None,
        close_rate=b_close_rate,
    )

    # Build after snapshot
    a_sales = _wagg(sales_rows, "sales_amt", req.qtr_after)
    a_sales_cnt = _wagg(sales_rows, "sales_cnt", req.qtr_after)
    a_flow = _wagg(flow_rows, "flow_total", req.qtr_after)
    a_store = _wagg(store_rows, "store_cnt", req.qtr_after)
    a_open = _wagg(store_rows, "open_cnt", req.qtr_after)
    a_close = _wagg(store_rows, "close_cnt", req.qtr_after)
    a_close_rate = round(a_close / a_store, 4) if a_close and a_store and a_store > 0 else None

    after = ComparisonMetricSnapshot(
        sales_amt=a_sales,
        sales_cnt=int(a_sales_cnt) if a_sales_cnt else None,
        flow_total=a_flow,
        store_cnt=int(a_store) if a_store else None,
        open_cnt=int(a_open) if a_open else None,
        close_cnt=int(a_close) if a_close else None,
        close_rate=a_close_rate,
    )

    # Change rates
    sales_cr = _safe_div(a_sales, b_sales)
    flow_cr = _safe_div(a_flow, b_flow)
    store_cr = _safe_div(a_store, b_store)

    change = ComparisonChange(
        sales_change_rate=sales_cr,
        sales_diff=round(a_sales - b_sales, 2) if a_sales is not None and b_sales is not None else None,
        flow_change_rate=flow_cr,
        flow_diff=round(a_flow - b_flow, 2) if a_flow is not None and b_flow is not None else None,
        store_change_rate=store_cr,
        store_diff=round(a_store - b_store, 2) if a_store is not None and b_store is not None else None,
    )

    # Breakdowns (from first available area)
    bkd_bh_before = bkd_bh_after = None
    bkd_wd_before = bkd_wd_after = None
    bkd_demo_before = bkd_demo_after = None
    for r in flow_rows:
        if r.qtr == req.qtr_before:
            bkd_bh_before = bkd_bh_before or r.flow_by_hour
            bkd_wd_before = bkd_wd_before or r.flow_by_weekday
            bkd_demo_before = bkd_demo_before or r.flow_by_demo
        elif r.qtr == req.qtr_after:
            bkd_bh_after = bkd_bh_after or r.flow_by_hour
            bkd_wd_after = bkd_wd_after or r.flow_by_weekday
            bkd_demo_after = bkd_demo_after or r.flow_by_demo

    breakdown = ComparisonBreakdown(
        flow_by_weekday_before=bkd_wd_before,
        flow_by_weekday_after=bkd_wd_after,
        flow_by_hour_before=bkd_bh_before,
        flow_by_hour_after=bkd_bh_after,
        flow_by_demo_before=bkd_demo_before,
        flow_by_demo_after=bkd_demo_after,
    )

    # Warnings
    warnings: list[str] = []
    if sales_cr is not None and sales_cr < -0.1:
        warnings.append(f"매출 {abs(sales_cr * 100):.1f}% 감소")
    if flow_cr is not None and flow_cr < -0.1:
        warnings.append(f"유동인구 {abs(flow_cr * 100):.1f}% 감소")
    if a_close_rate is not None and a_close_rate > 0.15:
        warnings.append(f"폐업률 {a_close_rate * 100:.1f}% (After 분기)")

    return ComparisonResponse(
        h3_index=req.h3_index,
        qtr_before=req.qtr_before,
        qtr_after=req.qtr_after,
        areas=area_names,
        before=before,
        after=after,
        change=change,
        breakdown=breakdown,
        warnings=warnings,
        data_asof=req.qtr_after,
    )
