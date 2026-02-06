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
