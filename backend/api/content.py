"""POST /api/content — content generation endpoints (4-cut stories, scripts)."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from agents.content_agent import content_agent_node
from api.schemas import StoryRequest, StoryResponse, StoryCut
from db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/content", tags=["content"])


@router.post("/story", response_model=StoryResponse)
async def create_story(request: StoryRequest, db: Session = Depends(get_db)):
    """Generate a 4-cut story from analysis data."""
    # Build context from analysis_run if provided
    kpis = request.kpis
    if request.analysis_run_id:
        row = db.execute(
            text("SELECT result_json, data_asof FROM analysis_run WHERE run_id = :rid"),
            {"rid": request.analysis_run_id},
        ).fetchone()
        if row and row.result_json:
            kpis = {**row.result_json, **kpis}

    question = f"{request.goal} 관련 4컷 스토리 생성"
    if request.area_name:
        question += f" (지역: {request.area_name})"

    state = {
        "question": question,
        "sql_result": {"rows": [kpis], "row_count": 1} if kpis else None,
        "insight": None,
        "data_asof": request.qtr,
    }

    result = await asyncio.to_thread(content_agent_node, state)
    brief = result.get("content_brief", {})

    cuts = []
    for c in brief.get("cuts", []):
        cuts.append(StoryCut(
            cut_number=c.get("cut_number", 0),
            title=c.get("title", ""),
            body=c.get("body", ""),
            kpi_ref=c.get("kpi_ref"),
            visual_hint=c.get("visual_hint"),
        ))

    # Save to content_brief table
    try:
        db.execute(
            text("""
                INSERT INTO content_brief (analysis_run_id, brief_type, goal, content_json, data_asof)
                VALUES (:arid, '4cut', :goal, :content, :asof)
            """),
            {
                "arid": request.analysis_run_id,
                "goal": request.goal,
                "content": json.dumps(brief, ensure_ascii=False),
                "asof": request.qtr,
            },
        )
        db.commit()
    except Exception:
        logger.exception("Failed to save content_brief")
        db.rollback()

    return StoryResponse(
        cuts=cuts,
        citations=brief.get("citations", []),
        data_asof=result.get("data_asof", ""),
    )
