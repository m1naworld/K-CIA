"""Shared fixtures for Phase 2-5 tests.

Uses FastAPI dependency override to inject a mock DB session,
so tests run without a real PostgreSQL connection.

Mocks h3 and langchain modules that may not be installed locally.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------
# Mock heavy native/external modules before importing backend code
# ---------------------------------------------------------------

def _ensure_mock_module(name: str, attrs: dict | None = None):
    """Install a mock module in sys.modules if not already importable."""
    try:
        __import__(name)
    except ImportError:
        mod = ModuleType(name)
        if attrs:
            for k, v in attrs.items():
                setattr(mod, k, v)
        sys.modules[name] = mod


# h3 library (C extension, may not build on all systems)
_ensure_mock_module("h3", {
    "latlng_to_cell": lambda lat, lng, res: "8a30e1c2c3fffff",
    "is_valid_cell": lambda idx: idx.startswith("8a") or idx.startswith("8b"),
    "cell_to_latlng": lambda idx: (37.5446, 127.0557),
    "grid_disk": lambda idx, k: [idx, "8a30e1c2c4fffff"],
})

# GeoAlchemy2
_ensure_mock_module("geoalchemy2")

# langchain / langgraph
_ensure_mock_module("langchain")
_ensure_mock_module("langchain.chat_models")
_ensure_mock_module("langchain_openai", {
    "ChatOpenAI": MagicMock,
})
_ensure_mock_module("langgraph")


class _FakeStateGraph:
    """Mock StateGraph that records nodes/edges and returns a compilable mock."""
    def __init__(self, *args, **kwargs):
        self._nodes = {}

    def add_node(self, name, fn):
        self._nodes[name] = fn

    def set_entry_point(self, name):
        pass

    def add_conditional_edges(self, source, fn, mapping):
        pass

    def add_edge(self, source, target):
        pass

    def compile(self):
        """Return a callable that mimics graph.invoke()."""
        mock_compiled = MagicMock()
        mock_compiled.invoke = lambda state: state
        return mock_compiled


_ensure_mock_module("langgraph.graph", {
    "StateGraph": _FakeStateGraph,
    "END": "END",
})
_ensure_mock_module("dotenv", {
    "load_dotenv": lambda *a, **kw: None,
})
_ensure_mock_module("asyncpg")
_ensure_mock_module("chardet")

# ---------------------------------------------------------------
# Now safe to import backend code
# ---------------------------------------------------------------

TESTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TESTS_DIR.parent / "backend"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from main import app
from db import get_db


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


@pytest.fixture
def fake_db():
    """Return a fresh FakeDB instance."""
    return FakeDB()


@pytest.fixture
def client(fake_db):
    """FastAPI TestClient with DB dependency overridden."""
    def _override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
