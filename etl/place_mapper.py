"""
LLM + Kakao Local based place → area_id resolver.

Workflow:
1) Extract place candidates from text with Gemini Flash
2) Geocode place with Kakao Local keyword search
3) Map coordinates to dim_area (COMMERCIAL_AREA) via spatial query
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import requests

from etl.db import execute_sql

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


PLACE_SYSTEM_PROMPT = """\
너는 성수동 상권 분석을 위한 장소 추출기다.
아래 SNS 콘텐츠(제목+내용)에서 실제 장소/상호/브랜드명을 우선으로 뽑아라.

## 우선순위
1) 상호/브랜드명 (예: 대림창고, 무신사 스튜디오, 어니언, 성수IT밸리)
2) 랜드마크/지명 (예: 연무장길, 서울숲, 뚝섬)
3) 주소가 명시되면 주소 텍스트 그대로 포함

## 규칙
- 각 콘텐츠마다 최대 3개까지 추출
- 상호가 없으면 지명만 추출해도 됨
- 일반 키워드(맛집/카페/핫플/팝업 등)는 제외
- 반드시 JSON 배열만 출력 (설명 금지)

## 입력 형식
번호. 제목 | 내용요약

## 출력 형식 (JSON만, 마크다운 금지)
[["대림창고", "연무장길"], ["성수IT밸리"], []]
"""


GENERIC_PLACES = {
    "성수",
    "성수동",
    "서울",
    "카페",
    "맛집",
    "핫플",
    "팝업",
}

ADDRESS_PATTERNS = [
    r"(서울(?:특별시)?\s*성동구\s*[가-힣0-9]+(?:로|길|동)\s*\d+(?:-\d+)?(?:\s*\d+층)?)",
    r"(성동구\s*[가-힣0-9]+(?:로|길|동)\s*\d+(?:-\d+)?)",
]

BUSINESS_SUFFIXES = (
    "점",
    "본점",
    "플래그십",
    "스토어",
    "카페",
    "베이커리",
    "공방",
    "스튜디오",
    "갤러리",
    "바",
    "식당",
    "라운지",
    "마켓",
    "편집샵",
    "살롱",
    "브루어리",
    "펍",
    "포토",
    "센터",
)


def _normalize_place(place: str) -> str:
    return place.strip().strip("\"'“”‘’")


def _normalize_business_name(place: str) -> str:
    name = _normalize_place(place)
    name = re.sub(r"\s*\([^\)]*\)\s*$", "", name)
    name = re.sub(r"\s*#.*$", "", name)
    name = re.sub(r"(\s*(성수|서울)?\s*)?(본점|지점|분점|점|1호점|2호점)$", "", name)
    name = re.sub(r"\s*(성수점|서울점)$", "", name)
    return name.strip()


def _place_score(place: str) -> int:
    score = 0
    for suffix in BUSINESS_SUFFIXES:
        if place.endswith(suffix):
            score += 3
            break
    if any(suffix in place for suffix in BUSINESS_SUFFIXES):
        score += 1
    if any(token in place for token in ("길", "거리", "역", "공원")):
        score += 1
    score += min(len(place), 20) // 4
    return score


def _rank_places(places: list[str]) -> list[str]:
    cleaned: list[str] = []
    for p in places:
        name = _normalize_place(p)
        if not name or name in GENERIC_PLACES:
            continue
        if name not in cleaned:
            cleaned.append(name)

    return sorted(cleaned, key=_place_score, reverse=True)


def extract_places_batch(
    snippets: list[dict[str, Any]],
    batch_size: int = 12,
) -> list[list[str]]:
    """Extract place candidates from snippets using Gemini Flash."""
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
                f"{PLACE_SYSTEM_PROMPT}\n\n{user_prompt}",
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 1024,
                },
            )
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

            parsed = json.loads(raw)
            if isinstance(parsed, list) and len(parsed) == len(batch):
                results.extend(parsed)
            else:
                results.extend([[] for _ in batch])
        except Exception as e:
            print(f"  [WARN] Gemini place extraction failed for batch {i}: {e}")
            results.extend([[] for _ in batch])

        if i + batch_size < len(snippets):
            time.sleep(0.5)

    return results


class PlaceResolver:
    def __init__(self, kakao_rest_key: str) -> None:
        self.kakao_rest_key = kakao_rest_key
        self._geo_cache: dict[str, tuple[float, float] | None] = {}
        self._area_cache: dict[str, int | None] = {}
        self._addr_cache: dict[str, int | None] = {}

    def resolve_area_ids(self, snippets: list[dict[str, Any]]) -> list[int | None]:
        """Resolve single best area_id per snippet (legacy interface)."""
        multi = self.resolve_area_ids_multi(snippets)
        return [ids[0] if ids else None for ids in multi]

    def resolve_area_ids_multi(
        self, snippets: list[dict[str, Any]],
    ) -> list[list[int]]:
        """Resolve ALL matching area_ids per snippet via geocoding.

        Pipeline per snippet:
        1. Extract street addresses → geocode → ST_Intersects
        2. Extract place/business names (Gemini) → geocode → ST_Intersects
        3. Return deduplicated list of all matched area_ids.
        """
        texts = [f"{s.get('title', '')} {s.get('snippet', '')}" for s in snippets]
        addresses_per = [extract_addresses(t) for t in texts]
        result: list[list[int]] = [[] for _ in snippets]

        # Phase 1: address-based geocoding
        for i, addr_list in enumerate(addresses_per):
            for addr in addr_list:
                area_id = self._area_id_from_address(addr)
                if area_id is not None and area_id not in result[i]:
                    result[i].append(area_id)

        # Phase 2: Gemini place extraction + Kakao geocoding for ALL snippets
        places_batch = extract_places_batch(snippets)
        for i, places in enumerate(places_batch):
            for place in _rank_places(places):
                area_id = self._area_id_from_place(place)
                if area_id is not None and area_id not in result[i]:
                    result[i].append(area_id)

        return result

    def _area_id_from_place(self, place: str) -> int | None:
        if place in self._area_cache:
            return self._area_cache[place]

        coords = self._geocode_place(place)
        if not coords:
            normalized = _normalize_business_name(place)
            if normalized and normalized != place:
                coords = self._geocode_place(normalized)
        if not coords:
            self._area_cache[place] = None
            return None

        area_id = self._area_id_from_coords(coords)
        self._area_cache[place] = area_id
        return area_id

    def _area_id_from_address(self, address: str) -> int | None:
        if address in self._addr_cache:
            return self._addr_cache[address]
        coords = self._kakao_address_search(address)
        if not coords:
            self._addr_cache[address] = None
            return None
        area_id = self._area_id_from_coords(coords)
        self._addr_cache[address] = area_id
        return area_id

    def _area_id_from_coords(self, coords: tuple[float, float]) -> int | None:
        lng, lat = coords
        result = execute_sql(
            """
            SELECT area_id
            FROM dim_area
            WHERE area_type = 'COMMERCIAL_AREA'
              AND ST_Intersects(geom, ST_SetSRID(ST_Point(:lng, :lat), 4326))
            LIMIT 1
            """,
            {"lng": lng, "lat": lat},
        )
        row = next(iter(result), None)
        return row[0] if row else None

    def _geocode_place(self, place: str) -> tuple[float, float] | None:
        if place in self._geo_cache:
            return self._geo_cache[place]

        if "성수" in place:
            coords = self._kakao_search(place)
            if not coords:
                coords = self._kakao_search(f"성수동 {place}")
        else:
            coords = self._kakao_search(f"성수동 {place}")
            if not coords:
                coords = self._kakao_search(place)

        self._geo_cache[place] = coords
        return coords

    def _kakao_search(self, query: str) -> tuple[float, float] | None:
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        try:
            response = requests.get(
                url,
                headers={"Authorization": f"KakaoAK {self.kakao_rest_key}"},
                params={"query": query, "size": 1},
                timeout=5,
            )
            if response.status_code != 200:
                return None
            data = response.json()
            docs = data.get("documents", [])
            if not docs:
                return None
            doc = docs[0]
            return float(doc["x"]), float(doc["y"])
        except Exception:
            return None

    def _kakao_address_search(self, query: str) -> tuple[float, float] | None:
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        try:
            response = requests.get(
                url,
                headers={"Authorization": f"KakaoAK {self.kakao_rest_key}"},
                params={"query": query},
                timeout=5,
            )
            if response.status_code != 200:
                return None
            data = response.json()
            docs = data.get("documents", [])
            if not docs:
                return None
            doc = docs[0]
            return float(doc["x"]), float(doc["y"])
        except Exception:
            return None


def extract_addresses(text: str) -> list[str]:
    matches: list[str] = []
    for pattern in ADDRESS_PATTERNS:
        for match in re.findall(pattern, text):
            addr = re.sub(r"\s+", " ", match).strip().strip("()[]{}.,;")
            if addr and addr not in matches:
                matches.append(addr)
    return matches


def build_place_resolver() -> PlaceResolver | None:
    kakao_key = os.getenv("KAKAO_REST_API_KEY")
    if not kakao_key:
        return None
    if _get_model() is None:
        return None
    return PlaceResolver(kakao_key)
