"""T3: Map Compare API tests (Phase 3 S4)."""

from __future__ import annotations

import pytest

from test_helpers import FakeRow, FakeResult


class TestCompareEndpoint:
    VALID_H3 = "8a30e1c2c3fffff"

    def test_invalid_h3_returns_400(self, client, fake_db):
        """T3-1 #2: Invalid H3 → 400."""
        resp = client.get("/api/map/hexagon/bad_h3/compare?qtr1=20243&qtr2=20244")
        assert resp.status_code == 400

    def test_h3_not_in_scope_returns_404(self, client, fake_db):
        """T3-1 #3: H3 not in scope → 404."""
        # _latest_quarters (or similar first query)
        fake_db.push_result(FakeResult(rows=[]))  # no areas found for this H3

        resp = client.get(f"/api/map/hexagon/{self.VALID_H3}/compare?qtr1=20243&qtr2=20244")
        assert resp.status_code == 404

    def test_valid_compare_returns_200(self, client, fake_db):
        """T3-1 #1: Valid comparison returns 200."""
        # Query 1: hex→area lookup (bridge_area_h3_weight JOIN dim_area)
        fake_db.push_result(FakeResult(rows=[
            FakeRow(area_id=1, area_name="성수역", weight=0.9)
        ]))
        # Query 2: sales comparison (GROUP BY area_id, qtr)
        fake_db.push_result(FakeResult(rows=[
            FakeRow(area_id=1, qtr="20243", sales_amt=1000000.0, sales_cnt=500),
            FakeRow(area_id=1, qtr="20244", sales_amt=1200000.0, sales_cnt=550),
        ]))
        # Query 3: flow comparison
        fake_db.push_result(FakeResult(rows=[
            FakeRow(area_id=1, qtr="20243", flow_total=40000.0,
                    flow_by_hour={"14": 3000}, flow_by_weekday=None),
            FakeRow(area_id=1, qtr="20244", flow_total=42000.0,
                    flow_by_hour={"14": 3200}, flow_by_weekday=None),
        ]))
        # Query 4: store comparison (GROUP BY area_id, qtr)
        fake_db.push_result(FakeResult(rows=[
            FakeRow(area_id=1, qtr="20243", store_cnt=50, close_cnt=2),
            FakeRow(area_id=1, qtr="20244", store_cnt=52, close_cnt=3),
        ]))
        # Query 5: avg_sales across preset_area_scope (GROUP BY qtr)
        fake_db.push_result(FakeResult(rows=[
            FakeRow(qtr="20243", avg_sales=900000.0),
            FakeRow(qtr="20244", avg_sales=1000000.0),
        ]))

        resp = client.get(
            f"/api/map/hexagon/{self.VALID_H3}/compare"
            "?qtr1=20243&qtr2=20244&area_type=COMMERCIAL_AREA"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["qtr1"] == "20243"
        assert data["qtr2"] == "20244"
        assert isinstance(data["comparisons"], list)
        assert len(data["comparisons"]) == 3  # 매출, 유동인구, 점포수
