"""Persist analysis_run rows for audit and reproducibility."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from db import engine


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def log_analysis_run(payload: dict[str, Any]) -> None:
    query = text(
        """
        INSERT INTO analysis_run (
            question,
            params_json,
            sql_text,
            result_json,
            assumptions_json,
            data_asof
        )
        VALUES (
            :question,
            :params_json::jsonb,
            :sql_text,
            :result_json::jsonb,
            :assumptions_json::jsonb,
            :data_asof::jsonb
        )
        """
    )

    params = {
        "question": payload.get("question"),
        "params_json": _json_or_none(payload.get("params_json")) or "{}",
        "sql_text": payload.get("sql_text"),
        "result_json": _json_or_none(payload.get("result_json")) or "{}",
        "assumptions_json": _json_or_none(payload.get("assumptions_json")) or "{}",
        "data_asof": _json_or_none(payload.get("data_asof")) or "{}",
    }

    with engine.begin() as conn:
        conn.execute(query, params)
