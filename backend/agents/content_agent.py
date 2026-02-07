"""Content Agent — generates structured 4-cut stories and scripts from analysis data."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from langchain_openai import ChatOpenAI

CONTENT_SYSTEM_PROMPT = """\
You are a content generation agent for 성수동 commercial district analysis.
You create persuasive, data-backed content in structured formats.

## Task
Given analysis data (KPIs, metrics, area info), generate a structured 4-cut story.

## 4-Cut Structure (훅/팩트/리스크/액션)
1. **훅 (Hook)**: 주의를 끄는 도입 (질문/놀라운 수치/트렌드)
2. **팩트 (Fact)**: 핵심 데이터 3개를 명확하게 제시
3. **리스크 (Risk)**: 주의해야 할 리스크/한계 (2개)
4. **액션 (Action)**: 구체적 행동 제안 (2-3개) + 체크리스트

## Rules
1. 모든 숫자는 한글 단위로 변환 (억원, 만명)
2. 각 컷 하단에 "기준: {분기}" 자동 표기
3. "본 자료는 공공데이터 기반 추정치이며, 실제 현장 확인이 필요합니다" 문구 포함
4. Respond in Korean
5. Return ONLY JSON format

## Response Format
{
  "cuts": [
    {"cut_number": 1, "title": "훅 제목", "body": "본문", "kpi_ref": "인용 수치", "visual_hint": "차트/이미지 제안"},
    {"cut_number": 2, "title": "팩트 제목", "body": "본문", "kpi_ref": "인용 수치", "visual_hint": "..."},
    {"cut_number": 3, "title": "리스크 제목", "body": "본문", "kpi_ref": "인용 수치", "visual_hint": "..."},
    {"cut_number": 4, "title": "액션 제목", "body": "본문", "kpi_ref": null, "visual_hint": "..."}
  ],
  "citations": ["KPI 출처 목록"],
  "data_asof": "기준 분기"
}
"""


def content_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: generate content from analysis results."""
    question = state["question"]
    sql_result = state.get("sql_result")
    insight = state.get("insight")
    data_asof = state.get("data_asof")

    user_content = f"콘텐츠 생성 요청: {question}"

    if isinstance(sql_result, dict) and sql_result.get("rows"):
        sample = sql_result["rows"][:10]
        user_content += f"\n\nSQL 데이터 ({sql_result.get('row_count', 0)}건):\n{json.dumps(sample, ensure_ascii=False, default=str)}"

    if insight:
        user_content += f"\n\n분석 인사이트:\n{json.dumps(insight, ensure_ascii=False, default=str)}"

    if data_asof:
        user_content += f"\n\n데이터 기준시점: {data_asof}"

    llm = ChatOpenAI(model="gpt-4o", temperature=0.5)
    response = llm.invoke([
        {"role": "system", "content": CONTENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ])

    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(content)
    except (json.JSONDecodeError, IndexError):
        parsed = {
            "cuts": [
                {"cut_number": 1, "title": "데이터 요약", "body": response.content, "kpi_ref": None, "visual_hint": None}
            ],
            "citations": [],
            "data_asof": data_asof or datetime.now().strftime("%Y-%m-%d"),
        }

    return {
        "content_brief": parsed,
        "data_asof": data_asof or datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
