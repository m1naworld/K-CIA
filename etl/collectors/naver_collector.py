"""Naver Search API Collector for Blog/Cafe trend analysis.

Quota: 25,000 calls/day (free). Each call returns up to 100 results.

Usage:
    from etl.collectors.naver_collector import NaverCollector

    collector = NaverCollector()
    results = collector.search_blog("성수동 카페", display=50)
    results = collector.search_cafe("성수동 맛집", display=50)
"""

from __future__ import annotations

import os
from typing import Any

import requests


class NaverAPIError(Exception):
    """Naver Search API error."""
    pass


class NaverCollector:
    """Collector for Naver Search API (Blog, Cafe)."""

    BASE_URL = "https://openapi.naver.com/v1/search"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise NaverAPIError(
                "NAVER_CLIENT_ID and NAVER_CLIENT_SECRET not found. "
                "Set them in .env file or pass to constructor."
            )
        self.session = requests.Session()
        self.session.headers.update({
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        })

    def _search(
        self,
        endpoint: str,
        query: str,
        display: int = 100,
        sort: str = "date",
    ) -> list[dict[str, Any]]:
        """Generic Naver search with pagination.

        Args:
            endpoint: "blog" or "cafearticle"
            query: Search keyword
            display: Results per page (max 100)
            sort: "date" (최신순) or "sim" (정확도순)

        Returns:
            List of result items
        """
        all_items: list[dict[str, Any]] = []
        start = 1
        per_page = min(display, 100)

        while len(all_items) < display:
            remaining = display - len(all_items)
            count = min(per_page, remaining)

            params = {
                "query": query,
                "display": count,
                "start": start,
                "sort": sort,
            }

            resp = self.session.get(
                f"{self.BASE_URL}/{endpoint}", params=params, timeout=30
            )

            if resp.status_code == 429:
                raise NaverAPIError("Naver API rate limit exceeded.")
            if resp.status_code != 200:
                raise NaverAPIError(
                    f"Naver API error {resp.status_code}: {resp.text[:200]}"
                )

            data = resp.json()
            items = data.get("items", [])
            if not items:
                break

            all_items.extend(items)

            # Naver API: start max 1000
            start += count
            if start > 1000:
                break
            if len(items) < count:
                break

        return all_items[:display]

    def search_blog(
        self,
        query: str,
        display: int = 100,
        sort: str = "date",
    ) -> list[dict[str, Any]]:
        """Search Naver Blog posts.

        Returns items with: title, link, description, bloggername,
        bloggerlink, postdate (YYYYMMDD)
        """
        return self._search("blog", query, display, sort)

    def search_cafe(
        self,
        query: str,
        display: int = 100,
        sort: str = "date",
    ) -> list[dict[str, Any]]:
        """Search Naver Cafe posts.

        Returns items with: title, link, description, cafename, cafeurl
        """
        return self._search("cafearticle", query, display, sort)


def test_naver_connection() -> bool:
    """Test Naver API connection with a minimal search."""
    try:
        collector = NaverCollector()
        items = collector.search_blog("성수동", display=1)
        print("✓ Naver API connection successful")
        if items:
            title = items[0].get("title", "")[:60]
            print(f"  Sample blog: {title}")
        return True
    except NaverAPIError as e:
        print(f"✗ Naver API error: {e}")
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


if __name__ == "__main__":
    test_naver_connection()
