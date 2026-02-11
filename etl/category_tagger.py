"""Gemini Flash 기반 소셜 콘텐츠 업종 태깅.

수집된 SNS 스니펫(title + snippet)을 Gemini Flash에 보내
관련 업종 카테고리 목록을 반환받는다.
ETL 저장 시점에 1회 호출하여 matched_categories에 저장.

Usage:
    from etl.category_tagger import tag_snippets_batch
    categories = tag_snippets_batch(snippets)  # list[list[str]]
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

_gemini_model = None


def _get_model():
    """Lazy-init Gemini Flash model."""
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        return _gemini_model
    except Exception as e:
        print(f"  [WARN] Gemini init failed: {e}")
        return None


SYSTEM_PROMPT = """\
너는 성수동 상권 분석 전문가다.
아래 SNS 콘텐츠(제목+내용)를 보고, 관련된 업종 카테고리를 모두 골라라.

## 업종 목록
커피, 음료, 한식, 중식, 일식, 양식, 치킨, 분식, 패스트푸드, 호프, 제과,
의류, 화장품, 미용, 인테리어, 갤러리, 팝업, 편집샵, 서점, 운동, 기타

## 규칙
- 각 콘텐츠에 대해 관련 업종을 1~3개 선택
- 명확하지 않으면 빈 배열 []
- 반드시 JSON 배열만 출력 (설명 금지)

## 입력 형식
번호. 제목 | 내용요약

## 출력 형식 (JSON만, 마크다운 금지)
[["커피", "제과"], ["일식"], [], ["팝업", "의류"]]
"""


def tag_snippets_batch(
    snippets: list[dict[str, Any]],
    batch_size: int = 15,
) -> list[list[str]]:
    """Tag a list of snippets with relevant categories using Gemini Flash.

    Args:
        snippets: list of dicts with 'title' and 'snippet' keys
        batch_size: max snippets per API call

    Returns:
        list of category lists, same length as snippets.
        Falls back to empty lists if Gemini unavailable.
    """
    model = _get_model()
    if model is None:
        return [[] for _ in snippets]

    results: list[list[str]] = []

    for i in range(0, len(snippets), batch_size):
        batch = snippets[i : i + batch_size]
        prompt_lines = []
        for j, s in enumerate(batch, 1):
            title = s.get("title", "")[:100]
            snippet_text = s.get("snippet", "")[:150]
            prompt_lines.append(f"{j}. {title} | {snippet_text}")

        user_prompt = "\n".join(prompt_lines)

        try:
            response = model.generate_content(
                f"{SYSTEM_PROMPT}\n\n{user_prompt}",
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 1024,
                },
            )
            raw = response.text.strip()
            # 마크다운 코드블록 제거
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

            parsed = json.loads(raw)
            if isinstance(parsed, list) and len(parsed) == len(batch):
                results.extend(parsed)
            else:
                # 길이 불일치 시 빈 배열로 채움
                results.extend([[] for _ in batch])
        except Exception as e:
            print(f"  [WARN] Gemini tagging failed for batch {i}: {e}")
            results.extend([[] for _ in batch])

        # Rate limit 방지
        if i + batch_size < len(snippets):
            time.sleep(0.5)

    return results
