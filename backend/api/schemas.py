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


class RiskCard(BaseModel):
    close_rate: float | None = None
    competition_density: float | None = None
    warnings: list[str] = []


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


class HexagonDetailResponse(BaseModel):
    h3_index: str
    lat: float
    lng: float
    qtr: str
    data_asof: str
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
