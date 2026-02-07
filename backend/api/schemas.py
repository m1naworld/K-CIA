"""Pydantic response models for Map API."""

from __future__ import annotations

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


# ---------- /api/map/hexagons/heatmap (Phase 2 S2) ----------

class HeatmapHexagon(BaseModel):
    h3_index: str
    lat: float
    lng: float
    area_name: str | None = None
    real_name: str | None = None
    flow_total: float | None = None
    values: dict = Field(default_factory=dict)


class HeatmapResponse(BaseModel):
    data: list[HeatmapHexagon]
    data_asof: str
    mode: str  # "hourly" or "weekday"


# ---------- /api/map/hexagon/{h3_index}/peaktime (Phase 2 S2) ----------

class PeaktimeAnalysis(BaseModel):
    h3_index: str
    qtr: str
    flow_total: float | None = None
    peak_hours: list[int] = []
    off_peak_hours: list[int] = []
    hourly_pattern: dict = Field(default_factory=dict)
    weekday_pattern: dict = Field(default_factory=dict)
    demo_breakdown: dict = Field(default_factory=dict)


# ---------- /api/map/hexagons/risk (Phase 2 S5) ----------

class RiskHexagon(BaseModel):
    h3_index: str
    lat: float
    lng: float
    area_name: str | None = None
    real_name: str | None = None
    risk_score: float = 0.0
    risk_factors: list[str] = []
    close_rate: float | None = None
    sales_qoq: float | None = None
    store_growth: float | None = None
    flow_qoq: float | None = None
    sales_amt: float | None = None


class RiskLayerResponse(BaseModel):
    data: list[RiskHexagon]
    data_asof: str


# ---------- /api/map/hexagon/{h3_index}/risk (Phase 2 S5) ----------

class RiskAnalysis(BaseModel):
    h3_index: str
    area_name: str | None = None
    real_name: str | None = None
    risk_score: float = 0.0
    risk_factors: list[str] = []
    close_rate: float | None = None
    sales_qoq: float | None = None
    store_growth: float | None = None
    flow_qoq: float | None = None
    alternative_areas: list[dict] = []
    data_asof: str = ""


# ---------- /api/map/hexagon/{h3_index}/compare (Phase 3 S4) ----------

class QuarterComparison(BaseModel):
    metric: str
    qtr1_value: float | None = None
    qtr2_value: float | None = None
    change_rate: float | None = None
    avg_change_rate: float | None = None
    above_avg: bool | None = None


class CompareResponse(BaseModel):
    h3_index: str
    qtr1: str
    qtr2: str
    comparisons: list[QuarterComparison] = []
    hourly_q1: dict | None = None
    hourly_q2: dict | None = None
    data_asof: str


# ---------- /api/content (Phase 4 S6) ----------

class StoryRequest(BaseModel):
    analysis_run_id: int | None = None
    goal: str = Field("입지추천", description="메시지 목표: 입지추천, 리스크경고, 운영최적화")
    kpis: dict = Field(default_factory=dict)
    area_name: str | None = None
    qtr: str | None = None


class StoryCut(BaseModel):
    cut_number: int
    title: str
    body: str
    kpi_ref: str | None = None
    visual_hint: str | None = None


class StoryResponse(BaseModel):
    cuts: list[StoryCut] = []
    citations: list[str] = []
    data_asof: str = ""
    warning: str = "본 자료는 공공데이터 기반 추정치이며, 실제 현장 확인이 필요합니다."


# ---------- /api/portfolio (Phase 5 S7/S8) ----------

class AssetInput(BaseModel):
    address: str
    category: str | None = None
    lat: float | None = None
    lng: float | None = None


class AssetHealth(BaseModel):
    asset_id: int
    address: str
    area_name: str | None = None
    health_status: str = "yellow"  # green, yellow, red
    health_score: float = 0.0
    demand_z: float | None = None
    competition_z: float | None = None
    growth_z: float | None = None
    risk_z: float | None = None
    top_factors: list[str] = []
    alternatives: list[dict] = []


class PortfolioMatrix(BaseModel):
    assets: list[AssetHealth] = []
    rebalance_suggestions: list[str] = []


class ABComparison(BaseModel):
    asset_a: AssetHealth
    asset_b: AssetHealth
    recommendation: str = ""
    sensitivity: dict = Field(default_factory=dict)


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
