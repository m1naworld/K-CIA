"""T1-3: Pydantic schema validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.schemas import (
    StoryRequest,
    StoryResponse,
    StoryCut,
    AssetInput,
    AssetHealth,
    PortfolioMatrix,
    ABComparison,
    ChatRequest,
    RiskHexagon,
    PeaktimeAnalysis,
    QuarterComparison,
    HeatmapHexagon,
)


class TestStoryRequest:
    def test_defaults(self):
        req = StoryRequest()
        assert req.goal == "입지추천"
        assert req.kpis == {}
        assert req.analysis_run_id is None
        assert req.area_name is None
        assert req.qtr is None

    def test_custom_goal(self):
        req = StoryRequest(goal="리스크경고")
        assert req.goal == "리스크경고"

    def test_with_kpis(self):
        req = StoryRequest(kpis={"sales": 100})
        assert req.kpis["sales"] == 100


class TestStoryResponse:
    def test_defaults(self):
        resp = StoryResponse()
        assert resp.cuts == []
        assert resp.citations == []
        assert resp.data_asof == ""
        assert "공공데이터" in resp.warning

    def test_with_cuts(self):
        cuts = [StoryCut(cut_number=1, title="훅", body="테스트")]
        resp = StoryResponse(cuts=cuts)
        assert len(resp.cuts) == 1
        assert resp.cuts[0].cut_number == 1


class TestAssetInput:
    def test_required_address(self):
        with pytest.raises(ValidationError):
            AssetInput()

    def test_valid_input(self):
        inp = AssetInput(address="성수동 123", lat=37.54, lng=127.05)
        assert inp.address == "성수동 123"
        assert inp.lat == 37.54

    def test_optional_fields(self):
        inp = AssetInput(address="성수동")
        assert inp.category is None
        assert inp.lat is None


class TestAssetHealth:
    def test_defaults(self):
        ah = AssetHealth(asset_id=1, address="test")
        assert ah.health_status == "yellow"
        assert ah.health_score == 0.0
        assert ah.top_factors == []
        assert ah.demand_z is None

    def test_all_fields(self):
        ah = AssetHealth(
            asset_id=1,
            address="test",
            health_status="green",
            health_score=0.8,
            demand_z=0.6,
            competition_z=0.3,
        )
        assert ah.health_status == "green"
        assert ah.demand_z == 0.6


class TestPortfolioMatrix:
    def test_empty(self):
        pm = PortfolioMatrix()
        assert pm.assets == []
        assert pm.rebalance_suggestions == []


class TestChatRequest:
    def test_empty_question_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(question="")

    def test_valid_question(self):
        req = ChatRequest(question="성수동 매출 Top3")
        assert req.question == "성수동 매출 Top3"
        assert req.messages == []


class TestRiskHexagon:
    def test_defaults(self):
        rh = RiskHexagon(h3_index="abc", lat=37.0, lng=127.0)
        assert rh.risk_score == 0.0
        assert rh.risk_factors == []
        assert rh.close_rate is None


class TestPeaktimeAnalysis:
    def test_defaults(self):
        pt = PeaktimeAnalysis(h3_index="abc", qtr="20243")
        assert pt.peak_hours == []
        assert pt.off_peak_hours == []
        assert pt.hourly_pattern == {}
        assert pt.weekday_pattern == {}


class TestQuarterComparison:
    def test_full(self):
        qc = QuarterComparison(
            metric="sales_amt",
            qtr1_value=100,
            qtr2_value=120,
            change_rate=0.2,
            avg_change_rate=0.1,
            above_avg=True,
        )
        assert qc.above_avg is True

    def test_null_values(self):
        qc = QuarterComparison(metric="flow_total")
        assert qc.qtr1_value is None
        assert qc.change_rate is None


class TestHeatmapHexagon:
    def test_defaults(self):
        hh = HeatmapHexagon(h3_index="abc", lat=37.0, lng=127.0)
        assert hh.values == {}
        assert hh.flow_total is None
