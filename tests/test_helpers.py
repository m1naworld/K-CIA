"""Shared test helpers — FakeRow, FakeResult, FakeDB.

Import from here in test files: `from tests.test_helpers import FakeRow, FakeResult`
Or with conftest's path manipulation: `from test_helpers import FakeRow, FakeResult`
"""

from __future__ import annotations


class FakeRow:
    """Lightweight row proxy that supports attribute + dict access."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._data = kwargs
        self._keys = list(kwargs.keys())

    def __getitem__(self, key):
        return self._data[key]

    def keys(self):
        return self._keys


class FakeResult:
    """Mimics SQLAlchemy CursorResult."""

    def __init__(self, rows: list[FakeRow] | None = None, scalar_value=None):
        self._rows = rows or []
        self._scalar = scalar_value

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar

    def keys(self):
        if self._rows:
            return self._rows[0].keys()
        return []


class FakeDB:
    """Mock SQLAlchemy Session that returns configurable results."""

    def __init__(self):
        self._results: list[FakeResult] = []
        self._call_idx = 0

    def push_result(self, result: FakeResult):
        """Queue a result for the next execute() call."""
        self._results.append(result)

    def execute(self, stmt, params=None):
        if self._call_idx < len(self._results):
            r = self._results[self._call_idx]
            self._call_idx += 1
            return r
        return FakeResult()

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass
