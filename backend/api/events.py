"""POST /api/events — ingest client analytics events."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from api.schemas import EventsRequest
from db import engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["events"])


def _insert_events(rows: list[dict]) -> None:
    query = text(
        """
        INSERT INTO event_log (event_type, session_id, user_id, props)
        VALUES (:event_type, :session_id, :user_id, :props::jsonb)
        """
    )
    with engine.begin() as conn:
        conn.execute(query, rows)


@router.post("/events")
async def ingest_events(payload: EventsRequest) -> dict:
    if not payload.events:
        return {"status": "ok", "inserted": 0}

    rows = []
    for event in payload.events:
        rows.append(
            {
                "event_type": event.event_type,
                "session_id": event.session_id,
                "user_id": event.user_id,
                "props": json.dumps(event.props, ensure_ascii=False, default=str),
            }
        )

    try:
        await asyncio.to_thread(_insert_events, rows)
    except Exception as exc:
        logger.exception("Failed to insert events")
        raise HTTPException(status_code=500, detail="Event log insert failed") from exc

    return {"status": "ok", "inserted": len(rows)}
