"""T5: Portfolio API tests (Phase 5 S7/S8)."""

from __future__ import annotations

import pytest

from test_helpers import FakeRow, FakeResult


# ---------------------------------------------------------------
# T5-1: POST /api/portfolio/assets
# ---------------------------------------------------------------

class TestRegisterAsset:
    def test_valid_registration(self, client, fake_db):
        """T5-1 #1: Valid asset registration."""
        # area lookup
        fake_db.push_result(FakeResult(rows=[
            FakeRow(area_id=1, area_name="성수역")
        ]))
        # INSERT RETURNING
        fake_db.push_result(FakeResult(scalar_value=42))

        resp = client.post("/api/portfolio/assets", json={
            "address": "성수동 2가 123",
            "lat": 37.5446,
            "lng": 127.0557,
            "category": "카페",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_id"] == 42
        assert data["h3_index"] is not None
        assert data["area_name"] == "성수역"

    def test_missing_lat_lng_returns_400(self, client, fake_db):
        """T5-1 #2: Missing lat/lng → 400."""
        resp = client.post("/api/portfolio/assets", json={
            "address": "성수동",
        })
        assert resp.status_code == 400
        assert "lat" in resp.json()["detail"].lower()


# ---------------------------------------------------------------
# T5-2: GET /api/portfolio/health
# ---------------------------------------------------------------

class TestPortfolioHealth:
    def test_no_assets_returns_empty(self, client, fake_db):
        """T5-2 #2: No assets → empty."""
        fake_db.push_result(FakeResult(rows=[]))

        resp = client.get("/api/portfolio/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["assets"] == []
        assert data["rebalance_suggestions"] == []

    def test_health_score_range(self, client, fake_db):
        """T5-2 #4: Health score is 0-1."""
        # dim_asset SELECT
        fake_db.push_result(FakeResult(rows=[
            FakeRow(asset_id=1, address="A", h3_index="8a30e1c2c3fffff",
                    area_id=1, category=None, user_id=None, lat=37.54, lng=127.05)
        ]))
        # _compute_health queries: bridge lookup → empty (triggers default)
        fake_db.push_result(FakeResult(rows=[]))  # bridge_area_h3_weight
        # latest quarters
        fake_db.push_result(FakeResult(rows=[]))

        resp = client.get("/api/portfolio/health")
        assert resp.status_code == 200
        assets = resp.json()["assets"]
        for a in assets:
            assert 0 <= a["health_score"] <= 1
            assert a["health_status"] in ("green", "yellow", "red")

    def test_health_status_values(self, client, fake_db):
        """T5-2 #3: Health status is green/yellow/red."""
        fake_db.push_result(FakeResult(rows=[
            FakeRow(asset_id=1, address="A", h3_index="8a30e1c2c3fffff",
                    area_id=1, category=None, user_id=None, lat=37.54, lng=127.05)
        ]))
        fake_db.push_result(FakeResult(rows=[]))

        resp = client.get("/api/portfolio/health")
        assert resp.status_code == 200
        for a in resp.json()["assets"]:
            assert a["health_status"] in ("green", "yellow", "red")


# ---------------------------------------------------------------
# T5-3: POST /api/portfolio/compare
# ---------------------------------------------------------------

class TestCompareAssets:
    def test_asset_not_found_returns_404(self, client, fake_db):
        """T5-3 #2: Non-existent asset → 404."""
        # asset A lookup
        fake_db.push_result(FakeResult(rows=[]))
        # asset B lookup
        fake_db.push_result(FakeResult(rows=[]))

        resp = client.post("/api/portfolio/compare?asset_a_id=999&asset_b_id=998")
        assert resp.status_code == 404

    def test_valid_compare(self, client, fake_db):
        """T5-3 #1: Valid comparison."""
        # asset A
        fake_db.push_result(FakeResult(rows=[
            FakeRow(asset_id=1, address="A", h3_index="8a30e1c2c3fffff",
                    area_id=1, category=None, lat=37.54, lng=127.05)
        ]))
        # asset B
        fake_db.push_result(FakeResult(rows=[
            FakeRow(asset_id=2, address="B", h3_index="8a30e1c2c4fffff",
                    area_id=2, category=None, lat=37.55, lng=127.06)
        ]))
        # _compute_health for A (bridge lookup + quarters + sales + flow + store)
        fake_db.push_result(FakeResult(rows=[]))  # bridge
        # _compute_health for B (bridge lookup)
        fake_db.push_result(FakeResult(rows=[]))  # bridge

        resp = client.post("/api/portfolio/compare?asset_a_id=1&asset_b_id=2")
        assert resp.status_code == 200
        data = resp.json()
        assert "asset_a" in data
        assert "asset_b" in data
        assert "recommendation" in data
        assert "sensitivity" in data
        # D14/D15 note
        assert "D14" in data["sensitivity"].get("note", "") or "D15" in data["sensitivity"].get("note", "")
