"""T2: Map API Phase 2 tests — heatmap, peaktime, risk endpoints."""

from __future__ import annotations

import pytest

from test_helpers import FakeRow, FakeResult


def _quarters_result(sales="20243", flow="20243", store="20243"):
    """Helper: create a FakeResult for _latest_quarters()."""
    rows = []
    if sales:
        rows.append(FakeRow(tbl="sales", qtr=sales))
    if flow:
        rows.append(FakeRow(tbl="flow", qtr=flow))
    if store:
        rows.append(FakeRow(tbl="store", qtr=store))
    return FakeResult(rows=rows)


# ---------------------------------------------------------------
# T2-1: GET /api/map/hexagons/heatmap
# ---------------------------------------------------------------

class TestHeatmapEndpoint:
    def test_hourly_mode_returns_200(self, client, fake_db):
        """T2-1 #1: Normal hourly mode."""
        fake_db.push_result(_quarters_result())  # _latest_quarters
        fake_db.push_result(FakeResult(rows=[
            FakeRow(
                h3_index="8a30e1c2c3fffff",
                area_id=1,
                area_name="성수역",
                real_name="연무장길",
                flow_total=50000.0,
                flow_by_hour={"0": 100, "14": 5000, "15": 4800},
                flow_by_weekday=None,
            )
        ]))

        resp = client.get("/api/map/hexagons/heatmap?mode=hourly&area_type=COMMERCIAL_AREA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "hourly"
        assert data["data_asof"] == "20243"

    def test_weekday_mode_returns_200(self, client, fake_db):
        """T2-1 #2: Weekday mode."""
        fake_db.push_result(_quarters_result())
        fake_db.push_result(FakeResult(rows=[
            FakeRow(
                h3_index="8a30e1c2c3fffff",
                area_id=1,
                area_name="성수역",
                real_name=None,
                flow_total=50000.0,
                flow_by_hour=None,
                flow_by_weekday={"MON": 7000, "TUE": 7200},
            )
        ]))

        resp = client.get("/api/map/hexagons/heatmap?mode=weekday&area_type=ADMIN_DONG")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "weekday"

    def test_empty_data_returns_empty_list(self, client, fake_db):
        """T2-1 #3: No data returns empty."""
        fake_db.push_result(_quarters_result())
        fake_db.push_result(FakeResult(rows=[]))

        resp = client.get("/api/map/hexagons/heatmap?mode=hourly")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_null_jsonb_returns_empty_values(self, client, fake_db):
        """T2-1 #4: NULL flow_by_hour → empty values dict."""
        fake_db.push_result(_quarters_result())
        fake_db.push_result(FakeResult(rows=[
            FakeRow(
                h3_index="8a30e1c2c3fffff",
                area_id=1,
                area_name="성수역",
                real_name=None,
                flow_total=50000.0,
                flow_by_hour=None,
                flow_by_weekday=None,
            )
        ]))

        resp = client.get("/api/map/hexagons/heatmap?mode=hourly")
        assert resp.status_code == 200
        items = resp.json()["data"]
        if items:
            assert items[0]["values"] == {}


# ---------------------------------------------------------------
# T2-2: GET /api/map/hexagon/{h3_index}/peaktime
# ---------------------------------------------------------------

class TestPeaktimeEndpoint:
    VALID_H3 = "8a30e1c2c3fffff"

    def test_valid_h3_returns_peaktime(self, client, fake_db):
        """T2-2 #1: Normal peaktime response."""
        fake_db.push_result(_quarters_result())  # _latest_quarters
        # flow data query
        fake_db.push_result(FakeResult(rows=[
            FakeRow(
                flow_total=50000.0,
                flow_by_hour={str(i): 1000 + i * 200 for i in range(24)},
                flow_by_weekday={"MON": 7000, "TUE": 7200, "WED": 7100,
                                  "THU": 7300, "FRI": 8000, "SAT": 9000, "SUN": 6000},
                flow_by_demo={"M_20": 3000, "F_20": 4000},
            )
        ]))

        resp = client.get(f"/api/map/hexagon/{self.VALID_H3}/peaktime?area_type=COMMERCIAL_AREA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["h3_index"] == self.VALID_H3
        assert len(data["peak_hours"]) == 3
        assert len(data["off_peak_hours"]) == 3
        assert all(isinstance(h, int) for h in data["peak_hours"])

    def test_no_flow_data_returns_404(self, client, fake_db):
        """T2-2 #2: No flow data → 404."""
        fake_db.push_result(_quarters_result())
        fake_db.push_result(FakeResult(rows=[]))  # no flow rows

        resp = client.get(f"/api/map/hexagon/{self.VALID_H3}/peaktime")
        assert resp.status_code == 404

    def test_invalid_h3_returns_400(self, client, fake_db):
        """T2-2 #3: Invalid H3 string → 400."""
        resp = client.get("/api/map/hexagon/invalid_h3/peaktime")
        assert resp.status_code == 400


# ---------------------------------------------------------------
# T2-3: GET /api/map/hexagons/risk
# ---------------------------------------------------------------

class TestRiskLayerEndpoint:
    def test_returns_risk_data(self, client, fake_db):
        """T2-3 #1: Normal risk layer returns 200."""
        # _latest_quarters
        fake_db.push_result(_quarters_result())
        # hex_areas query (the big CTE)
        fake_db.push_result(FakeResult(rows=[
            FakeRow(
                h3_index="8a30e1c2c3fffff",
                area_id=1,
                area_name="성수역",
                real_name="연무장길",
                cur_sales=1000000.0,
                prev_sales=1100000.0,
                cur_store=50,
                prev_store=48,
                close_cnt=5,
                open_cnt=3,
                cur_flow=40000.0,
                prev_flow=45000.0,
            )
        ]))

        resp = client.get("/api/map/hexagons/risk?area_type=COMMERCIAL_AREA")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "data_asof" in data
        # Verify risk score is in valid range
        for item in data["data"]:
            assert 0 <= item["risk_score"] <= 1


# ---------------------------------------------------------------
# T2-4: GET /api/map/hexagon/{h3_index}/risk
# ---------------------------------------------------------------

class TestRiskDetailEndpoint:
    VALID_H3 = "8a30e1c2c3fffff"

    def test_invalid_h3_returns_400(self, client, fake_db):
        """T2-4 #2: Invalid H3 → 400."""
        resp = client.get("/api/map/hexagon/bad_h3/risk")
        assert resp.status_code == 400
