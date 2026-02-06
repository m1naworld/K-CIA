"""POST /api/chat — SSE streaming endpoint wrapping the LangGraph agent."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from agents.graph import build_graph
from api.schemas import ChatRequest
from services.analysis_logger import log_analysis_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# Build graph once at module level.
_graph = build_graph()


def _sse_event(event: str, data: dict) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_chat(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Run the LangGraph agent and emit SSE events from the result."""
    try:
        # Convert messages to dict format for agents
        history = [{"role": m.role, "content": m.content} for m in request.messages]
        
        inputs = {
            "question": request.question,
            "messages": history,
            "area_type": request.area_type,
            "category": request.category,
            "qtr": request.qtr,
            "selected_hex_detail": request.selected_hex_detail,
        }

        result = await asyncio.to_thread(_graph.invoke, inputs)

        params_json = {
            "area_type": request.area_type,
            "category": request.category,
            "qtr": request.qtr,
            "route": result.get("route"),
            "messages": history[-6:],
            "selected_hex_detail": request.selected_hex_detail,
        }
        result_json = {
            "sql_result": result.get("sql_result"),
            "insight": result.get("insight"),
        }
        insight = result.get("insight") or {}
        assumptions_json = {
            "assumptions": insight.get("assumptions"),
            "checklist": insight.get("checklist"),
        }
        data_asof = result.get("data_asof")

        try:
            await asyncio.to_thread(
                log_analysis_run,
                {
                    "question": request.question,
                    "params_json": params_json,
                    "sql_text": result.get("sql_text"),
                    "result_json": result_json,
                    "assumptions_json": assumptions_json,
                    "data_asof": data_asof,
                },
            )
        except Exception:
            logger.exception("Failed to log analysis_run")

        # routing event
        route = result.get("route", "insight")
        yield _sse_event("routing", {"route": route})

        # sql event (if SQL agent ran)
        sql_text = result.get("sql_text")
        if sql_text is not None:
            sql_result = result.get("sql_result")
            # sql_result is dict: {"columns": [...], "rows": [...], "row_count": N}
            # or string if error: "[BLOCKED] ..." or "[SQL_ERROR] ..."
            if isinstance(sql_result, dict):
                row_count = sql_result.get("row_count", 0)
            else:
                row_count = 0
            yield _sse_event("sql", {"sql": sql_text, "row_count": row_count})

        # insight event (if insight agent ran)
        insight = result.get("insight")
        if insight is not None:
            yield _sse_event("insight", insight)
        elif sql_text is not None:
            sql_result = result.get("sql_result")
            if isinstance(sql_result, dict) and sql_result.get("rows"):
                rows = sql_result["rows"]
                row_count = sql_result.get("row_count", len(rows))
                sample_rows = rows[:5]
                sample_text = "\n".join([str(r) for r in sample_rows])
                if row_count > 5:
                    sample_text += f"\n... 외 {row_count - 5}건"
                fallback_insight = {
                    "summary": f"SQL 쿼리 결과 {row_count}건이 조회되었습니다.",
                    "evidence": [f"총 {row_count}건의 데이터가 반환되었습니다.", f"상위 결과 예시:\n{sample_text}"],
                    "risks": [],
                    "recommendations": ["상세 분석이 필요하시면 '분석해줘'라고 추가 질문해 주세요."],
                    "checklist": [],
                }
                yield _sse_event("insight", fallback_insight)
            elif isinstance(sql_result, str):
                yield _sse_event("insight", {
                    "summary": "SQL 실행 중 오류가 발생했습니다.",
                    "evidence": [sql_result],
                    "risks": ["쿼리 조건을 다시 확인해 주세요."],
                    "recommendations": [],
                    "checklist": [],
                })

        # done
        data_asof = result.get("data_asof", "unknown")
        yield _sse_event("done", {"data_asof": data_asof})

    except Exception:
        logger.exception("Chat stream error")
        yield _sse_event("error", {"message": "내부 서버 오류가 발생했습니다."})


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """SSE streaming chat endpoint."""
    return StreamingResponse(
        _stream_chat(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
