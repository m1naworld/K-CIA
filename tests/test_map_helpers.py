"""T1: Unit tests for map.py helper functions."""

from __future__ import annotations

import pytest

from api.map import _prev_quarter, _safe_div


class TestPrevQuarter:
    """T1-1: _prev_quarter() tests."""

    def test_normal_quarter(self):
        assert _prev_quarter("20243") == "20242"

    def test_q1_wraps_to_prev_year(self):
        assert _prev_quarter("20241") == "20234"

    def test_year_boundary(self):
        assert _prev_quarter("20251") == "20244"

    def test_q4_to_q3(self):
        assert _prev_quarter("20244") == "20243"

    def test_q2_to_q1(self):
        assert _prev_quarter("20242") == "20241"


class TestSafeDiv:
    """T1-2: _safe_div() tests."""

    def test_normal_growth(self):
        result = _safe_div(110, 100)
        assert result == pytest.approx(0.1, abs=0.0001)

    def test_zero_denominator(self):
        assert _safe_div(100, 0) is None

    def test_none_numerator(self):
        assert _safe_div(None, 100) is None

    def test_none_denominator(self):
        assert _safe_div(100, None) is None

    def test_both_none(self):
        assert _safe_div(None, None) is None

    def test_zero_to_zero(self):
        # 0 / 0 → None (zero denominator)
        assert _safe_div(0, 0) is None

    def test_decrease(self):
        result = _safe_div(90, 100)
        assert result == pytest.approx(-0.1, abs=0.0001)

    def test_large_growth(self):
        result = _safe_div(200, 100)
        assert result == pytest.approx(1.0, abs=0.0001)
