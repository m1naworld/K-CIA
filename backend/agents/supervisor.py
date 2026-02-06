"""Supervisor agent — routes user queries to sql_agent or insight_agent."""

from __future__ import annotations

import json
from typing import Any

from langchain_openai import ChatOpenAI

ROUTING_SYSTEM_PROMPT = """\
You are a query router for a commercial district analysis system (성수동, Seoul).

Classify the user's question into exactly ONE route:

- "sql"     : ONLY for extremely simple data lookup with no explanation needed
              User explicitly says "숫자만", "데이터만", "쿼리만"
              Examples: "매출 숫자만 알려줘", "raw 데이터만"

- "insight" : Pure qualitative queries that don't need current data at all
              Keywords: 왜/전략/조언/어떻게 해야
              Examples: "카페 창업 전략이 뭐야?", "왜 성수동이 인기야?"

- "both"    : DEFAULT for most questions - needs data + analysis/explanation
              Use this for:
              - Any data request (매출/유동인구/점포수) → user wants explanation too
              - 분석/분석해줘/알려줘/설명해줘/변환해줘
              - 추이/트렌드/변화
              - 추천/적합한/좋은 곳
              - Questions ending with "~라고 보면 될까?", "~인 건가?", "~일까?", "~궁금해"
              - Calculation + explanation (e.g., "일기준으로 변환해줘", "카페별 매출")
              - Follow-up questions (references to previous context)
              Examples: "매출 알려줘", "카페 매출 Top3", "추이 분석해줘", "~는 어때?"

IMPORTANT: When in doubt, ALWAYS choose "both". It's safer to provide insight than miss it.

Respond with ONLY a JSON object: {"route": "sql"|"insight"|"both"}
"""


def route_query(question: str) -> str:
    """Classify a question and return route: 'sql', 'insight', or 'both'."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    response = llm.invoke([
        {"role": "system", "content": ROUTING_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ])
    try:
        parsed = json.loads(response.content)
        route = parsed.get("route", "both")
    except (json.JSONDecodeError, AttributeError):
        route = "both"
    if route not in ("sql", "insight", "both"):
        route = "both"
    return route


def supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: determine route for the question."""
    question = state["question"]
    route = route_query(question)
    return {"route": route}
