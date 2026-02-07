"""T4: Content API tests (Phase 4 S6)."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from test_helpers import FakeRow, FakeResult


MOCK_CONTENT_BRIEF = {
    "cuts": [
        {"cut_number": 1, "title": "훅", "body": "성수동이 뜨고 있다!", "kpi_ref": "매출 120%", "visual_hint": "그래프"},
        {"cut_number": 2, "title": "팩트", "body": "매출 데이터 3개", "kpi_ref": None, "visual_hint": None},
        {"cut_number": 3, "title": "리스크", "body": "폐업률 주의", "kpi_ref": None, "visual_hint": None},
        {"cut_number": 4, "title": "액션", "body": "현장 조사 필요", "kpi_ref": None, "visual_hint": None},
    ],
    "citations": ["서울 열린데이터광장 D1"],
    "data_asof": "20243",
}


class TestStoryEndpoint:
    @patch("api.content.content_agent_node")
    def test_basic_story_generation(self, mock_agent, client, fake_db):
        """T4-1 #1: Basic story request returns 200."""
        mock_agent.return_value = {
            "content_brief": MOCK_CONTENT_BRIEF,
            "data_asof": "20243",
        }
        # For content_brief INSERT (may fail silently)
        fake_db.push_result(FakeResult())  # commit result

        resp = client.post("/api/content/story", json={
            "goal": "입지추천",
            "qtr": "20243",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["cuts"]) == 4
        assert data["data_asof"] == "20243"

    @patch("api.content.content_agent_node")
    def test_4cut_structure(self, mock_agent, client, fake_db):
        """T4-1 #2: Response has exactly 4 cuts."""
        mock_agent.return_value = {
            "content_brief": MOCK_CONTENT_BRIEF,
            "data_asof": "20243",
        }
        fake_db.push_result(FakeResult())

        resp = client.post("/api/content/story", json={"goal": "리스크경고"})
        assert resp.status_code == 200
        cuts = resp.json()["cuts"]
        assert len(cuts) == 4

    @patch("api.content.content_agent_node")
    def test_cut_numbers_sequential(self, mock_agent, client, fake_db):
        """T4-1 #3: Cut numbers are 1-4 in order."""
        mock_agent.return_value = {
            "content_brief": MOCK_CONTENT_BRIEF,
            "data_asof": "20243",
        }
        fake_db.push_result(FakeResult())

        resp = client.post("/api/content/story", json={})
        cuts = resp.json()["cuts"]
        numbers = [c["cut_number"] for c in cuts]
        assert numbers == [1, 2, 3, 4]

    @patch("api.content.content_agent_node")
    def test_citations_present(self, mock_agent, client, fake_db):
        """T4-1 #4: Citations are a list."""
        mock_agent.return_value = {
            "content_brief": MOCK_CONTENT_BRIEF,
            "data_asof": "20243",
        }
        fake_db.push_result(FakeResult())

        resp = client.post("/api/content/story", json={})
        citations = resp.json()["citations"]
        assert isinstance(citations, list)
        assert len(citations) > 0

    @patch("api.content.content_agent_node")
    def test_warning_default(self, mock_agent, client, fake_db):
        """T4-1 #5: Warning contains disclaimer."""
        mock_agent.return_value = {
            "content_brief": MOCK_CONTENT_BRIEF,
            "data_asof": "20243",
        }
        fake_db.push_result(FakeResult())

        resp = client.post("/api/content/story", json={})
        warning = resp.json()["warning"]
        assert "공공데이터" in warning

    @patch("api.content.content_agent_node")
    def test_analysis_run_id_lookup(self, mock_agent, client, fake_db):
        """T4-1 #6: analysis_run_id triggers DB lookup."""
        mock_agent.return_value = {
            "content_brief": MOCK_CONTENT_BRIEF,
            "data_asof": "20243",
        }
        # analysis_run SELECT
        fake_db.push_result(FakeResult(rows=[
            FakeRow(result_json={"sales": 50000}, data_asof="20243")
        ]))
        # content_brief INSERT
        fake_db.push_result(FakeResult())

        resp = client.post("/api/content/story", json={
            "analysis_run_id": 1,
            "goal": "운영최적화",
        })
        assert resp.status_code == 200
        # Verify agent was called (merged KPIs)
        mock_agent.assert_called_once()
