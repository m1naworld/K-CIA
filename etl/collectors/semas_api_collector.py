"""소상공인시장진흥공단 상가정보 API Collector.

행정동별 점포 좌표를 수집하여 H3 기반 weight 계산에 활용.

Usage:
    from etl.collectors.semas_api_collector import SemasAPICollector

    collector = SemasAPICollector()
    stores = collector.fetch_stores_by_dong("11200650")  # 성수1가1동
    stores = collector.fetch_all_seongsu()  # 성수동 4개 동 전체
"""

from __future__ import annotations

import os
import time
import urllib.parse
from typing import Any

import requests


# API 설정
SEMAS_API_BASE_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2"
DEFAULT_PAGE_SIZE = 1000  # API 최대 1000건 제한
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 2.0  # seconds
DEFAULT_RATE_LIMIT_DELAY = 0.5  # seconds between requests

# 성수동 4개 동 코드 (8자리)
SEONGSU_DONG_CODES = [
    "11200650",  # 성수1가1동
    "11200660",  # 성수1가2동
    "11200670",  # 성수2가1동
    "11200690",  # 성수2가3동
]


class SemasAPIError(Exception):
    """소상공인 API 에러."""
    pass


class SemasAPICollector:
    """소상공인시장진흥공단 상가정보 API 수집기.

    행정동별 점포 목록을 조회하여 좌표(경도/위도)와 업종 정보를 수집합니다.
    """

    def __init__(
        self,
        api_key: str | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        retry_count: int = DEFAULT_RETRY_COUNT,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY,
    ):
        self.api_key = api_key or os.getenv("SEMAS_API_KEY")
        if not self.api_key:
            raise SemasAPIError(
                "SEMAS_API_KEY not found. "
                "Set it in .env file or pass to constructor."
            )

        self.page_size = min(page_size, 1000)  # API 제한
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()

    def _build_url(self, endpoint: str) -> str:
        """Build API URL for the given endpoint."""
        return f"{SEMAS_API_BASE_URL}/{endpoint}"

    def _fetch_page(
        self,
        dong_code: str,
        page_no: int = 1,
    ) -> dict[str, Any]:
        """Fetch a single page of stores for a dong with retry logic.

        Args:
            dong_code: 행정동코드 (8자리)
            page_no: 페이지 번호 (1부터 시작)

        Returns:
            API 응답 JSON
        """
        # requests params= double-encodes '+' in API key, breaking auth
        assert self.api_key is not None
        encoded_key = urllib.parse.quote(self.api_key, safe="")
        url = (
            f"{SEMAS_API_BASE_URL}/storeListInDong"
            f"?serviceKey={encoded_key}"
            f"&divId=adongCd"
            f"&key={dong_code}"
            f"&pageNo={page_no}"
            f"&numOfRows={self.page_size}"
            f"&type=json"
        )

        last_error = None
        for attempt in range(self.retry_count):
            try:
                response = self.session.get(url, timeout=60)
                response.raise_for_status()

                # JSON 파싱
                data = response.json()

                # API 응답 구조 확인
                # 성공: {"body": {"items": [...], "totalCount": N, ...}, "header": {"resultCode": "00", ...}}
                # 실패: {"header": {"resultCode": "XX", "resultMsg": "..."}}

                header = data.get("header", {})
                result_code = header.get("resultCode", "")

                if result_code == "00":
                    return data
                elif result_code == "03":
                    # 데이터 없음
                    return {"_empty": True, "body": {"items": [], "totalCount": 0}}
                else:
                    raise SemasAPIError(
                        f"API Error [{result_code}]: {header.get('resultMsg', 'Unknown')}"
                    )

            except requests.RequestException as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise SemasAPIError(f"Request failed after {self.retry_count} retries: {e}")
            except ValueError as e:
                # JSON 파싱 에러
                raise SemasAPIError(f"JSON parse error: {e}")

        raise SemasAPIError(f"Request failed: {last_error}")

    def fetch_stores_by_dong(
        self,
        dong_code: str,
        max_records: int | None = None,
        progress_callback: Any | None = None,
    ) -> list[dict[str, Any]]:
        """행정동별 점포 목록 전체 조회 (자동 페이지네이션).

        Args:
            dong_code: 행정동코드 (8자리)
            max_records: 최대 수집 건수 (None이면 전체)
            progress_callback: 진행률 콜백 함수 (fetched_count, total_count)

        Returns:
            점포 정보 딕셔너리 리스트
        """
        all_stores: list[dict[str, Any]] = []
        page_no = 1
        total_count = None

        print(f"  Fetching stores for dong {dong_code}...")

        while True:
            data = self._fetch_page(dong_code, page_no)

            # 데이터 없음 체크
            if data.get("_empty"):
                break

            body = data.get("body", {})

            # 전체 건수 파악 (첫 호출에서만)
            if total_count is None:
                total_count = body.get("totalCount", 0)
                print(f"    Total records: {total_count:,}")

            # 점포 데이터 추출
            items = body.get("items", [])
            if not items:
                break

            all_stores.extend(items)

            # 진행률 콜백
            if progress_callback:
                progress_callback(len(all_stores), total_count)

            # 종료 조건
            if len(items) < self.page_size:
                break
            if max_records and len(all_stores) >= max_records:
                break
            if total_count and len(all_stores) >= total_count:
                break

            # Rate limiting
            time.sleep(self.rate_limit_delay)
            page_no += 1

        print(f"    Fetched {len(all_stores):,} stores")
        return all_stores

    def fetch_all_seongsu(
        self,
        max_records_per_dong: int | None = None,
    ) -> list[dict[str, Any]]:
        """성수동 4개 동 전체 점포 수집.

        Args:
            max_records_per_dong: 동별 최대 수집 건수 (테스트용)

        Returns:
            전체 점포 정보 리스트 (dong_code 필드 추가됨)
        """
        all_stores: list[dict[str, Any]] = []

        print(f"Fetching all Seongsu-dong stores ({len(SEONGSU_DONG_CODES)} dongs)...")

        for dong_code in SEONGSU_DONG_CODES:
            stores = self.fetch_stores_by_dong(dong_code, max_records_per_dong)

            # dong_code 필드 추가 (나중에 참조용)
            for store in stores:
                store["_dong_code"] = dong_code

            all_stores.extend(stores)

            # 동 간 rate limiting
            time.sleep(self.rate_limit_delay * 2)

        print(f"Total: {len(all_stores):,} stores from {len(SEONGSU_DONG_CODES)} dongs")
        return all_stores

    @staticmethod
    def parse_store(raw: dict[str, Any]) -> dict[str, Any]:
        """API 원본 데이터를 정규화된 딕셔너리로 변환.

        Args:
            raw: API 응답의 개별 점포 데이터

        Returns:
            정규화된 점포 딕셔너리
        """
        return {
            "store_id": raw.get("bizesId"),           # 상가업소번호
            "store_name": raw.get("bizesNm"),         # 상호명
            "branch_name": raw.get("brchNm"),         # 지점명
            "inds_l_cd": raw.get("indsLclsCd"),       # 대분류코드
            "inds_l_nm": raw.get("indsLclsNm"),       # 대분류명
            "inds_m_cd": raw.get("indsMclsCd"),       # 중분류코드
            "inds_m_nm": raw.get("indsMclsNm"),       # 중분류명
            "inds_s_cd": raw.get("indsSclsCd"),       # 소분류코드
            "inds_s_nm": raw.get("indsSclsNm"),       # 소분류명
            "addr_road": raw.get("rdnmAdr"),          # 도로명주소
            "lng": _safe_float(raw.get("lon")),       # 경도
            "lat": _safe_float(raw.get("lat")),       # 위도
            "adong_cd": raw.get("adongCd"),           # 행정동코드
        }


def _safe_float(val: Any) -> float | None:
    """안전하게 float으로 변환."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def test_api_connection() -> bool:
    """API 연결 테스트."""
    try:
        collector = SemasAPICollector()

        # 첫 동에서 1건만 조회
        dong_code = SEONGSU_DONG_CODES[0]
        collector.page_size = 1

        data = collector._fetch_page(dong_code, 1)

        if data.get("_empty"):
            print(f"✓ API connection successful (no data for {dong_code})")
            return True

        body = data.get("body", {})
        total_count = body.get("totalCount", 0)
        items = body.get("items", [])

        print(f"✓ API connection successful")
        print(f"  Dong: {dong_code}")
        print(f"  Total records: {total_count:,}")
        if items:
            sample = items[0]
            print(f"  Sample: {sample.get('bizesNm')} ({sample.get('indsLclsNm')})")

        return True

    except SemasAPIError as e:
        print(f"✗ API error: {e}")
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


if __name__ == "__main__":
    test_api_connection()
