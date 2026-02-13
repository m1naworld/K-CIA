"""Insight Agent — structures qualitative responses with evidence, risks, recommendations."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from langchain_openai import ChatOpenAI

INSIGHT_SYSTEM_PROMPT = """\
You are a commercial district insight analyst for 성수동 (Seoul).
Your job is to help users understand commercial district data with ACTIONABLE INSIGHTS.

Given a user question and SQL query results, produce a structured JSON response.
CRITICAL: Always provide INSIGHTS and ANALYSIS, not just raw data.

## STEP 1: CLASSIFY THE QUESTION TYPE

| Type | Keywords | Response Cards |
|------|----------|----------------|
| DATA_LOOKUP | "알려줘", "보여줘", "Top3", "순위", "얼마", "몇 개", "비율" | summary + data_table + insights + context |
| RECOMMENDATION | "추천", "적합", "창업", "차려도 될까", "어디가 좋아" | summary + recommendations + evidence + risks + checklist |
| RISK_ANALYSIS | "리스크", "위험", "주의", "문제", "폐업" | summary + risks + evidence + action_items |
| COMPARISON | "비교", "vs", "차이", "대비" | summary + comparison + evidence |
| GENERAL | 기타 | summary + evidence |

## STEP 2: USE THE CORRECT RESPONSE FORMAT

### TYPE: DATA_LOOKUP (데이터 조회 + 인사이트)
Use when user asks for specific data like "Top3 알려줘", "유동인구 순위", "매출 보여줘"
IMPORTANT: Even for data lookups, provide ANALYSIS and INSIGHTS, not just numbers.

{
  "response_type": "data_lookup",
  "summary": "핵심 결론 1-2문장 (구체적 숫자 + 의미 해석 포함)",
  "data_table": [
    {"rank": 1, "area_name": "상권명", "value": "251.7만명", "description": "왜 이 상권이 높은지 한 줄 설명"},
    {"rank": 2, "area_name": "상권명", "value": "198.3만명", "description": "특징 설명"},
    ...
  ],
  "insights": [
    "데이터에서 발견한 핵심 패턴/트렌드 (예: '1위와 2위 격차가 27% 차이로 뚝섬역이 압도적')",
    "이 결과가 의미하는 바 (예: '20대 여성 타겟 팝업스토어는 뚝섬역 집중 고려')",
    "주의할 점이나 추가 고려사항"
  ],
  "context": {
    "data_period": "2024년 4분기",
    "area_scope": "성수동 17개 상권",
    "note": "분기 유동인구 합계 기준"
  }
}

KEY RULES for DATA_LOOKUP:
1. data_table의 value는 반드시 읽기 쉬운 형태로 (251.7만명, 35.6억원)
2. insights는 3개 이상 - 단순 나열이 아닌 "왜?", "그래서?", "주의할 점" 분석 필수
3. description에서 각 상권의 특성 설명 (카페거리, IT밸리 등)

### TYPE: RECOMMENDATION (상권 추천/창업 상담)
Use when user asks for business advice like "창업 추천", "적합한 곳", "차려도 될까"

{
  "response_type": "recommendation",
  "summary": "결론 요약 1-2문장",
  "recommendations": [
    {
      "rank": 1,
      "area_name": "상권명",
      "reason": "추천 이유 (데이터 기반, 구체적 수치 포함)",
      "metrics": {"매출": "35.6억원", "유동인구": "251.7만명", "점포수": "42개"},
      "fit_score": "적합도 (상/중/하)"
    },
    ...
  ],
  "evidence": ["구체적 숫자 인용 3개 - 반드시 SQL 결과에서 추출"],
  "risks": [
    {"level": "high|medium|low", "description": "고려해야 할 리스크", "mitigation": "대응 방안"}
  ],
  "checklist": ["현장 방문 전 확인 사항", "추가 조사 필요 사항"]
}

### TYPE: RISK_ANALYSIS (리스크 진단)
Use when user asks about risks like "리스크가 뭐야", "위험 요소", "주의할 점"

{
  "response_type": "risk_analysis",
  "summary": "리스크 요약",
  "risks": [
    {"level": "high|medium|low", "description": "리스크 설명", "data": "근거 데이터"}
  ],
  "evidence": ["리스크 판단 근거"],
  "action_items": ["리스크 대응 방안"]
}

### TYPE: COMPARISON (비교 분석)
Use when user asks to compare like "A vs B", "비교해줘", "차이가 뭐야"

{
  "response_type": "comparison",
  "summary": "비교 결론",
  "comparison": {
    "items": ["A", "B"],
    "metrics": [
      {"name": "매출", "A": "...", "B": "...", "winner": "A|B|tie"},
      ...
    ]
  },
  "evidence": ["비교 근거"]
}

### TYPE: GENERAL (일반 질문)
{
  "response_type": "general",
  "summary": "답변",
  "evidence": ["관련 정보"],
  "insights": ["추가 인사이트가 있다면"]
}

## NUMBER FORMATTING:
- 매출: 억원 단위 (1000000000 = 10억원, 35억6천 → 35.6억원)
- 유동인구: 만명 단위 (10000 = 1만명, 2517162 → 251.7만명)
- 비율: 소수점 1자리 % (0.5142 → 51.4%)

## CRITICAL RULES:
1. FIRST classify the question type, THEN choose the response format
2. **ALWAYS provide insights and analysis** - never just list raw data
3. For DATA_LOOKUP: Include "insights" array with 3+ analytical observations
4. Parse ALL SQL result rows and include them in data_table
5. Always include response_type field
6. Respond in Korean
7. Return ONLY JSON, no markdown fences
8. **summary는 반드시 구체적 숫자와 의미 해석을 포함** (예: "뚝섬역이 251.7만명으로 1위이며, 2위 성수역(198.3만명) 대비 27% 높습니다")
9. **insights에서 "왜 이런 결과가 나왔는지", "사업적으로 어떤 의미인지" 분석 필수**
10. If social_result is provided (SNS module ON), incorporate social buzz/sentiment/keywords into your analysis.
    - Reference specific social evidence (blog/YouTube mentions) to support or contrast quantitative data.
    - If sentiment is negative despite good sales data, flag as a risk.
    - Include top social keywords in your insights.
    - If social_result is None (module OFF), add a note: "소셜 데이터 미포함 — 현장 방문 및 온라인 리뷰 확인 권장" in checklist.
"""


def insight_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: generate structured insight from question + optional SQL results."""
    question = state["question"]
    sql_result = state.get("sql_result")
    data_asof = state.get("data_asof")
    selected_hex_detail = state.get("selected_hex_detail")

    user_content = f"질문: {question}"
    
    if selected_hex_detail:
        primary_area_name = selected_hex_detail.get("primary_area_name")
        if primary_area_name:
            user_content += f"\n\n선택한 상권명: {primary_area_name}"
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
    
    # M9: Social trend data
    social_result = state.get("social_result")
    if social_result and social_result.get("total_buzz", 0) > 0:
        user_content += (
            f"\n\n소셜 트렌드 데이터 (최근 30일):\n"
            f"- 총 버즈량: {social_result['total_buzz']}건\n"
            f"- 평균 감성: {social_result.get('avg_sentiment', 'N/A')}\n"
            f"- 긍정/부정: {social_result.get('total_pos', 0)}/{social_result.get('total_neg', 0)}\n"
            f"- TOP 키워드: {social_result.get('top_keywords', [])[:10]}\n"
            f"- 소스별: {json.dumps(social_result.get('by_source', []), ensure_ascii=False)}\n"
        )
        evidence = social_result.get("evidence_snippets", [])[:5]
        if evidence:
            user_content += "- 주요 언급:\n"
            for ev in evidence:
                user_content += f"  [{ev.get('source','')}] {ev.get('title','')[:80]}\n"
        print(f"[Insight] Social data injected: buzz={social_result['total_buzz']}", flush=True)
    elif social_result is None:
        user_content += "\n\n[참고] 소셜 데이터 모듈이 비활성화 상태입니다."

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
