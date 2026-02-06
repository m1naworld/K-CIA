"""Seoul Open API Collector with pagination, retry, and rate limiting.

Usage:
    from etl.collectors.seoul_api_collector import SeoulAPICollector
    
    collector = SeoulAPICollector()
    data = collector.fetch_all("VwsmTrdarSelngQq")  # D1 추정매출
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests

# API 서비스명 (서울 열린데이터광장)
# D1: 추정매출(상권) - VwsmTrdarSelngQq
# D2: 점포(행정동) - VwsmAdstrdStorQq  
# D5: 유동인구(상권) - VwsmTrdarFlpopQq
# D11: 실시간 도시데이터 - citydata_ppltn

API_SERVICES = {
    "D1_SALES": "VwsmTrdarSelngQq",      # 상권분석서비스(추정매출-상권) OA-15572
    "D2_STORE": "VwsmAdstrdStorW",        # 상권분석서비스(점포-행정동) OA-22172
    "D2_STORE_TRDAR": "VwsmTrdarStorQq",  # 상권분석서비스(점포-상권) OA-15574
    "D5_FLOW": "VwsmTrdarFlpopQq",       # 상권분석서비스(유동인구-상권) OA-15568
    "D11_REALTIME": "citydata",          # 실시간 도시데이터 OA-21285 (장소별 호출)
    "AREA_INFO": "TbgisTrdarRelm",       # 상권영역정보 OA-15560 (상권코드+좌표+면적)
}

# 기본 설정
BASE_URL = "http://openapi.seoul.go.kr:8088"
DEFAULT_PAGE_SIZE = 1000  # API 최대 1000건 제한
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 2.0  # seconds
DEFAULT_RATE_LIMIT_DELAY = 0.5  # seconds between requests


class SeoulAPIError(Exception):
    """Seoul Open API error."""
    pass


class SeoulAPICollector:
    """Collector for Seoul Open Data API with automatic pagination."""
    
    def __init__(
        self,
        api_key: str | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        retry_count: int = DEFAULT_RETRY_COUNT,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY,
    ):
        self.api_key = api_key or os.getenv("SEOUL_API_KEY")
        if not self.api_key:
            raise SeoulAPIError(
                "SEOUL_API_KEY not found. "
                "Set it in .env file or pass to constructor."
            )
        
        self.page_size = min(page_size, 1000)  # API 제한
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
    
    def _build_url(
        self,
        service: str,
        start: int,
        end: int,
        extra_params: list[str] | None = None,
    ) -> str:
        """Build API URL with pagination.
        
        Format: {BASE_URL}/{KEY}/json/{SERVICE}/{START}/{END}/{EXTRA...}
        """
        parts = [
            BASE_URL,
            self.api_key,
            "json",
            service,
            str(start),
            str(end),
        ]
        if extra_params:
            parts.extend(extra_params)
        return "/".join(parts)
    
    def _fetch_page(
        self,
        service: str,
        start: int,
        end: int,
        extra_params: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fetch a single page with retry logic."""
        url = self._build_url(service, start, end, extra_params)
        
        last_error = None
        for attempt in range(self.retry_count):
            try:
                response = self.session.get(url, timeout=60)
                response.raise_for_status()
                data = response.json()
                
                # API 에러 체크
                if service in data:
                    result_info = data[service].get("RESULT", {})
                    code = result_info.get("CODE", "")
                    
                    if code == "INFO-000":
                        return data
                    elif code == "INFO-200":
                        # 데이터 없음 - 정상 종료 신호
                        return {"_empty": True, "_service": service}
                    else:
                        raise SeoulAPIError(
                            f"API Error [{code}]: {result_info.get('MESSAGE', 'Unknown')}"
                        )
                else:
                    # 응답 구조 확인
                    if "RESULT" in data:
                        result = data["RESULT"]
                        if result.get("CODE") == "INFO-200":
                            return {"_empty": True, "_service": service}
                        raise SeoulAPIError(
                            f"API Error [{result.get('CODE')}]: {result.get('MESSAGE')}"
                        )
                    return data
                    
            except requests.RequestException as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise SeoulAPIError(f"Request failed after {self.retry_count} retries: {e}")
        
        raise SeoulAPIError(f"Request failed: {last_error}")
    
    def fetch_all(
        self,
        service: str,
        extra_params: list[str] | None = None,
        max_records: int | None = None,
        progress_callback: Any | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all records with automatic pagination.
        
        Args:
            service: API service name (e.g., "VwsmTrdarSelngQq")
            extra_params: Additional URL path parameters
            max_records: Optional limit on total records
            progress_callback: Optional callback(fetched_count, total_count)
            
        Returns:
            List of all row dictionaries
        """
        all_rows: list[dict[str, Any]] = []
        start = 1
        total_count = None
        
        while True:
            end = start + self.page_size - 1
            if max_records:
                end = min(end, max_records)
            
            data = self._fetch_page(service, start, end, extra_params)
            
            # 데이터 없음 체크
            if data.get("_empty"):
                break
            
            # 서비스 데이터 추출
            if service not in data:
                raise SeoulAPIError(f"Unexpected response structure: {list(data.keys())}")
            
            service_data = data[service]
            
            # 전체 건수 파악 (첫 호출에서만)
            if total_count is None:
                total_count = service_data.get("list_total_count", 0)
                print(f"  Total records available: {total_count:,}")
            
            # 행 데이터 추출
            rows = service_data.get("row", [])
            if not rows:
                break
            
            all_rows.extend(rows)
            
            # 진행률 콜백
            if progress_callback:
                progress_callback(len(all_rows), total_count)
            
            # 종료 조건
            if len(rows) < self.page_size:
                break
            if max_records and len(all_rows) >= max_records:
                break
            if total_count and len(all_rows) >= total_count:
                break
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            start = end + 1
        
        return all_rows
    
    def fetch_service(
        self,
        service_key: str,
        extra_params: list[str] | None = None,
        max_records: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch by service key (D1_SALES, D2_STORE, D5_FLOW, D11_REALTIME).
        
        Args:
            service_key: One of API_SERVICES keys
            extra_params: Additional parameters
            max_records: Optional limit
            
        Returns:
            List of all row dictionaries
        """
        if service_key not in API_SERVICES:
            raise SeoulAPIError(
                f"Unknown service key: {service_key}. "
                f"Available: {list(API_SERVICES.keys())}"
            )
        
        service = API_SERVICES[service_key]
        print(f"Fetching {service_key} ({service})...")
        
        return self.fetch_all(service, extra_params, max_records)


def test_api_connection() -> bool:
    """Test API connection with a small request."""
    try:
        collector = SeoulAPICollector()
        # 1건만 조회해서 연결 테스트
        url = collector._build_url(API_SERVICES["D1_SALES"], 1, 1)
        response = collector.session.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        service = API_SERVICES["D1_SALES"]
        if service in data:
            result = data[service].get("RESULT", {})
            code = result.get("CODE", "")
            if code == "INFO-000":
                print(f"✓ API connection successful")
                print(f"  Total records: {data[service].get('list_total_count', 'N/A')}")
                return True
            else:
                print(f"✗ API error: [{code}] {result.get('MESSAGE', '')}")
                return False
        else:
            print(f"✗ Unexpected response: {list(data.keys())}")
            return False
            
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


if __name__ == "__main__":
    test_api_connection()
