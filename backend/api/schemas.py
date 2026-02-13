"""Pydantic response models for Map API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------- /api/map/hexagons ----------

class HexagonSummary(BaseModel):
    h3_index: str
    lat: float
    lng: float
    area_id: int | None = None
    area_name: str | None = None
    real_name: str | None = None
    sales_amt: float | None = None
    sales_cnt: int | None = None
    flow_total: float | None = None
    store_cnt: int | None = None
    open_cnt: int | None = None
    close_cnt: int | None = None
    sales_qoq: float | None = None  # QoQ sales growth rate (ratio)
    peak_hour: str | None = None  # peak time slot key e.g. "17_21"
    peak_hour_ratio: float | None = None  # share of peak time slot flow / total
    weekday_ratio: float | None = None  # weekday flow / (weekday + weekend) flow
    # Risk mode (M11-2)
    risk_score: float | None = None  # composite risk score 0-100
    risk_level: str | None = None  # "High" | "Medium" | "Low"


class HexagonsResponse(BaseModel):
    data: list[HexagonSummary]
    data_asof: str
    area_type: str
    weight_type: str = "store"  # "store" (점포 수 기반) or "area" (면적 기반)
    filters: dict


# ---------- /api/map/hexagon/{h3_index} ----------

class FlowCard(BaseModel):
    flow_total: float | None = None
    flow_by_hour: dict | None = None
    flow_by_weekday: dict | None = None
    flow_by_demo: dict | None = None


class SalesCard(BaseModel):
    sales_amt: float | None = None
    sales_cnt: int | None = None


class CompetitionCard(BaseModel):
    store_cnt: int | None = None
    open_cnt: int | None = None
    close_cnt: int | None = None
    close_rate: float | None = None
    competition_density: float | None = None


class GrowthCard(BaseModel):
    sales_growth_rate: float | None = None
    flow_growth_rate: float | None = None
    store_growth_rate: float | None = None


class RiskDecompositionItem(BaseModel):
    """Single factor contributing to the composite risk score."""
    factor: str  # "close_rate" | "store_growth" | "sales_decline" | "competition_density"
    label: str  # "폐업률" | "점포 증가율" | "매출 감소" | "경쟁 밀도"
    value: float | None = None  # raw metric value
    score: float = 0  # normalized score 0-100
    weight: float = 0  # factor weight (sum=1.0)
    contribution: float = 0  # weight × score


class RiskCard(BaseModel):
    risk_score: float | None = None  # composite 0-100
    risk_level: str | None = None  # "High" | "Medium" | "Low"
    close_rate: float | None = None
    competition_density: float | None = None
    warnings: list[str] = []
    decomposition: list[RiskDecompositionItem] = []


class AlternativeArea(BaseModel):
    """A lower-risk alternative hexagon recommended as substitute."""
    h3_index: str
    area_name: str | None = None
    risk_score: float
    risk_level: str  # "High" | "Medium" | "Low"
    flow_total: float | None = None
    sales_amt: float | None = None
    store_cnt: int | None = None
    close_rate: float | None = None
    sales_qoq: float | None = None


class RecommendationCard(BaseModel):
    score: int = Field(0, ge=0, le=100, description="Suitability score 0-100")
    grade: str = Field("C", description="Grade: S/A/B/C/D")
    pros: list[str] = []
    cons: list[str] = []
    summary: str = ""


class TrendPoint(BaseModel):
    qtr: str
    value: float | None = None


class TrendData(BaseModel):
    sales: list[TrendPoint] = []
    flow: list[TrendPoint] = []
    store: list[TrendPoint] = []


class FacilityItem(BaseModel):
    facility_type: str
    label: str
    count: int


class FacilityCard(BaseModel):
    total_count: int = 0
    facilities: list[FacilityItem] = []
    top_types: list[str] = []  # top 5 facility labels


class DemoGenderRatio(BaseModel):
    male: float | None = None
    female: float | None = None


class DemoAgeItem(BaseModel):
    age_group: str  # "10", "20", "30", "40", "50", "60+"
    ratio: float
    count: float


class DemoCard(BaseModel):
    gender: DemoGenderRatio = DemoGenderRatio()
    age_distribution: list[DemoAgeItem] = []
    peak_age_group: str | None = None
    peak_gender: str | None = None


class TimeSlotItem(BaseModel):
    hour_range: str  # "11~14", "17~21"
    label: str  # "점심", "저녁"
    flow_ratio: float  # share of daily flow


class TimeSlotRecommendation(BaseModel):
    peak_hours: list[int] = []  # top 3 hours (0-23)
    peak_weekday: str | None = None  # "월"~"일"
    off_peak_hours: list[int] = []
    recommendations: list[TimeSlotItem] = []


# ---------- Operating Strategy Card (M10-2) ----------

class TimeSlotStrategy(BaseModel):
    """Single time-slot operating strategy."""
    hour_range: str  # "11~14"
    label: str  # "점심"
    flow_ratio: float  # share of total flow (0~1)
    estimated_revenue_share: float  # estimated revenue contribution (유동 기반 추정)
    staff_ratio: float  # relative staff allocation (avg=1.0, peak>1.0, off-peak<1.0)
    is_peak: bool  # True if this slot is in peak group


class WeekdayPattern(BaseModel):
    """Weekday vs weekend flow pattern."""
    weekday_flow_ratio: float | None = None  # 평일 유동 비중
    weekend_flow_ratio: float | None = None  # 주말 유동 비중
    peak_day: str | None = None  # 최고 유동 요일 ("월"~"일")
    peak_day_flow: float | None = None  # 최고 요일 유동인구


class OperatingStrategyCard(BaseModel):
    """Operating strategy recommendations based on time-slot flow patterns."""
    recommended_open: str  # "06:00"
    recommended_close: str  # "24:00"
    recommended_hours: int  # 권장 영업 시간 수
    peak_slots: list[TimeSlotStrategy] = []  # top 2~3 slots (피크)
    off_peak_slots: list[TimeSlotStrategy] = []  # bottom slots (오프피크)
    all_slots: list[TimeSlotStrategy] = []  # all 6 slots ordered by time
    weekday_pattern: WeekdayPattern | None = None
    total_flow: float | None = None  # 총 유동인구
    assumptions: list[str] = []  # 가정 목록


class HexagonDetailResponse(BaseModel):
    h3_index: str
    lat: float
    lng: float
    qtr: str
    data_asof: str
    primary_area_name: str | None = None
    areas: list[str]
    flow: FlowCard
    sales: SalesCard
    competition: CompetitionCard
    growth: GrowthCard
    risk: RiskCard
    recommendation: RecommendationCard
    trend: TrendData
    facility: FacilityCard | None = None
    demo: DemoCard | None = None
    time_slot: TimeSlotRecommendation | None = None
    operating_strategy: OperatingStrategyCard | None = None
    # Risk decomposition + alternatives (M11-3)
    alternatives: list[AlternativeArea] = []


# ---------- /api/map/compare ----------

class ComparisonRequest(BaseModel):
    h3_index: str = Field(..., description="H3 hexagon index")
    qtr_before: str = Field(..., description="Before quarter (e.g. '20243')")
    qtr_after: str = Field(..., description="After quarter (e.g. '20244')")
    area_type: str = Field("COMMERCIAL_AREA", pattern="^(COMMERCIAL_AREA|ADMIN_DONG)$")
    category: str | None = None


class ComparisonMetricSnapshot(BaseModel):
    sales_amt: float | None = None
    sales_cnt: int | None = None
    flow_total: float | None = None
    store_cnt: int | None = None
    open_cnt: int | None = None
    close_cnt: int | None = None
    close_rate: float | None = None


class ComparisonChange(BaseModel):
    sales_change_rate: float | None = None
    sales_diff: float | None = None
    flow_change_rate: float | None = None
    flow_diff: float | None = None
    store_change_rate: float | None = None
    store_diff: float | None = None


class ComparisonBreakdown(BaseModel):
    flow_by_weekday_before: dict | None = None
    flow_by_weekday_after: dict | None = None
    flow_by_hour_before: dict | None = None
    flow_by_hour_after: dict | None = None
    flow_by_demo_before: dict | None = None
    flow_by_demo_after: dict | None = None


class ComparisonResponse(BaseModel):
    h3_index: str
    qtr_before: str
    qtr_after: str
    areas: list[str] = []
    before: ComparisonMetricSnapshot
    after: ComparisonMetricSnapshot
    change: ComparisonChange
    breakdown: ComparisonBreakdown | None = None
    warnings: list[str] = []
    data_asof: str


# ---------- /api/chat ----------

class ChatMessage(BaseModel):
    """A single message in the conversation history."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    messages: list[ChatMessage] = Field(default_factory=list, description="Previous conversation history")
    area_type: str | None = None
    category: str | None = None
    qtr: str | None = None
    selected_hex_detail: dict | None = None


# ---------- /api/events ----------

class EventIn(BaseModel):
    event_type: str = Field(..., min_length=1)
    session_id: str | None = None
    user_id: str | None = None
    props: dict = Field(default_factory=dict)


class EventsRequest(BaseModel):
    events: list[EventIn] = Field(default_factory=list)
