"""Insight Agent — structures qualitative responses with evidence, risks, recommendations."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from langchain_openai import ChatOpenAI

INSIGHT_SYSTEM_PROMPT = """\
You are a commercial district insight analyst for 성수동 (Seoul).

Given a user question and SQL query results, produce a structured JSON response.

## CRITICAL: READ SQL DATA CAREFULLY
- SQL results are provided as JSON array of objects
- Each row = one data point. Parse ALL rows, not just the first one.
- If user asks for "3개 추천" and SQL returns 3 rows, create 3 recommendations.
- flow_total = 유동인구, sales_amt = 매출, store_cnt = 점포수

## RESPONSE FORMAT:

### For Recommendation Questions (추천, 적합한 곳, 창업, 차려도)
When SQL returns multiple rows for recommendation:

{
  "summary": "결론 요약 1-2문장",
  "recommendations": [
    {
      "rank": 1,
      "area_name": "첫번째 row의 area_name",
      "reason": "추천 이유",
      "metrics": {
        "매출": "sales_amt를 억원 단위로 변환 (예: 3564698777 → 35.6억원)",
        "점포수": "store_cnt 값 + '개'",
        "유동인구": "flow_total을 만명 단위로 변환 (예: 2517162 → 251.7만명)"
      }
    },
    {
      "rank": 2,
      "area_name": "두번째 row의 area_name",
      ...
    },
    ... (SQL 결과 row 개수만큼)
  ],
  "evidence": ["구체적 숫자 인용 근거 3개"],
  "risks": ["데이터 기반 구체적 리스크"],
  "action_items": ["구체적 행동 제안"],
  "checklist": ["확인 필요 사항"]
}

### For Operation Strategy Questions (운영전략, 피크타임, 인력, 영업시간)
{
  "summary": "운영전략 요약",
  "peak_analysis": {
    "peak_hours": ["14시", "15시", "16시"],
    "off_peak_hours": ["6시", "7시"],
    "weekday_peak": "토요일",
    "target_demo": "20-30대 여성"
  },
  "recommendations": [
    {"type": "인력", "detail": "피크타임(14-17시) 인력 +1명 권장"},
    {"type": "프로모션", "detail": "오프피크(10-12시) 할인 이벤트"}
  ],
  "evidence": ["피크타임 유동인구 비중 42%"],
  "risks": ["주말 집중 리스크"],
  "assumptions": ["객단가 12,000원 가정", "회전율 2.5회/좌석"]
}

### For Risk Analysis Questions (리스크, 폐업, 경쟁과밀, 포화)
{
  "summary": "리스크 진단 결론",
  "risk_score": 0.65,
  "risk_breakdown": [
    {"factor": "폐업률", "contribution": 0.3, "detail": "폐업률 18.5%"},
    {"factor": "매출 감소", "contribution": 0.25, "detail": "QoQ -12.3%"},
    {"factor": "경쟁 과밀", "contribution": 0.1, "detail": "점포 +15% 증가"}
  ],
  "alternative_areas": ["연무장길 (리스크 0.2, 매출 35.6억)", "서울숲 입구 (리스크 0.15, 매출 12.3억)"],
  "evidence": ["데이터 기반 사실"],
  "recommendations": ["구체적 제안"],
  "checklist": ["확인 필요 사항"]
}

### For Simple Data Queries
{
  "summary": "핵심 답변 (숫자 포함)",
  "evidence": ["데이터 기반 사실"]
}

## NUMBER FORMATTING:
- 매출: 억원 단위 (1000000000 = 10억원)
- 유동인구: 만명 단위 (10000 = 1만명)
- flow_total이 NULL이 아니면 반드시 표시할 것!

## CRITICAL Rules:
1. SQL 결과의 모든 row를 recommendations에 포함
2. NULL이 아닌 값을 "데이터 없음"으로 표시하지 말 것
3. 숫자는 반드시 한글 단위로 변환 (억원, 만명)
4. Respond in Korean
5. Return ONLY JSON, no markdown fences
"""


def insight_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: generate structured insight from question + optional SQL results."""
    question = state["question"]
    sql_result = state.get("sql_result")
    data_asof = state.get("data_asof")
    selected_hex_detail = state.get("selected_hex_detail")

    user_content = f"질문: {question}"
    
    if selected_hex_detail:
        user_content += (
            "\n\n선택한 상권 카드 데이터(요약 카드):\n"
            f"{json.dumps(selected_hex_detail, ensure_ascii=False, default=str)}"
        )

    # Check if we have valid SQL results
    has_data = False
    if isinstance(sql_result, dict):
        row_count = sql_result.get("row_count", 0)
        rows = sql_result.get("rows", [])
        has_data = row_count > 0 and len(rows) > 0
        
        print(f"[Insight] sql_result type={type(sql_result)}, row_count={row_count}, rows_len={len(rows)}", flush=True)
        
        if has_data:
            # Pass first 20 rows to LLM
            sample_rows = rows[:20]
            user_content += f"\n\nSQL 결과 데이터 ({row_count}건, 상위 20건 표시):\n{json.dumps(sample_rows, ensure_ascii=False, default=str)}"
            print(f"[Insight] Passing {len(sample_rows)} sample rows to LLM", flush=True)
        else:
            user_content += "\n\n[주의] SQL 쿼리 결과가 0건입니다. 해당 조건에 맞는 데이터가 없습니다."
            print("[Insight] No data in rows", flush=True)
    elif isinstance(sql_result, str) and sql_result.startswith("["):
        # Error case
        user_content += f"\n\n[주의] SQL 오류 발생: {sql_result}"
        print(f"[Insight] SQL error: {sql_result[:100]}", flush=True)
    else:
        user_content += "\n\n[주의] SQL 데이터가 제공되지 않았습니다. 일반적인 도메인 지식 기반으로 답변해주세요."
        print(f"[Insight] No sql_result, type={type(sql_result)}", flush=True)
    
    if data_asof:
        user_content += f"\n\n데이터 기준시점: {data_asof}"

    # Build conversation context
    messages_history = state.get("messages", [])
    llm_messages = [{"role": "system", "content": INSIGHT_SYSTEM_PROMPT}]
    
    # Add conversation history (last 6 messages for context)
    for msg in messages_history[-6:]:
        llm_messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current question with SQL result
    llm_messages.append({"role": "user", "content": user_content})

    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    response = llm.invoke(llm_messages)

    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        insight = json.loads(content)
    except (json.JSONDecodeError, IndexError):
        insight = {"summary": response.content, "parse_error": True}

    if not data_asof:
        data_asof = datetime.now().strftime("%Y-%m-%d %H:%M")

    return {
        "insight": insight,
        "data_asof": data_asof,
    }
