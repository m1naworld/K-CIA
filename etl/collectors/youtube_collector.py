"""YouTube Data API v3 Collector for SNS trend analysis.

Quota: 100 units per search.list call → 10K units/day → ~100 searches/day.

Usage:
    from etl.collectors.youtube_collector import YouTubeCollector

    collector = YouTubeCollector()
    videos = collector.search("성수동 카페", days=30, max_results=50)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


class YouTubeAPIError(Exception):
    """YouTube Data API error."""
    pass


class YouTubeCollector:
    """Collector for YouTube Data API v3 (search.list)."""

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise YouTubeAPIError(
                "YOUTUBE_API_KEY not found. "
                "Set it in .env file or pass to constructor."
            )
        self.session = requests.Session()

    def search(
        self,
        query: str,
        days: int = 30,
        max_results: int = 50,
        region_code: str = "KR",
    ) -> list[dict[str, Any]]:
        """Search YouTube videos by keyword.

        Args:
            query: Search keyword (e.g., "성수동 카페")
            days: Look back N days from today
            max_results: Max videos to return (API max 50 per page)
            region_code: ISO 3166-1 alpha-2 country code

        Returns:
            List of video metadata dicts with keys:
            video_id, title, description, published_at, channel_title
        """
        published_after = (
            datetime.now(timezone.utc) - timedelta(days=days)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        all_videos: list[dict[str, Any]] = []
        page_token: str | None = None

        while len(all_videos) < max_results:
            per_page = min(50, max_results - len(all_videos))
            params: dict[str, Any] = {
                "key": self.api_key,
                "part": "snippet",
                "q": query,
                "type": "video",
                "order": "date",
                "publishedAfter": published_after,
                "regionCode": region_code,
                "relevanceLanguage": "ko",
                "maxResults": per_page,
            }
            if page_token:
                params["pageToken"] = page_token

            resp = self.session.get(
                f"{self.BASE_URL}/search", params=params, timeout=30
            )

            if resp.status_code == 403:
                error_data = resp.json()
                reason = (
                    error_data.get("error", {})
                    .get("errors", [{}])[0]
                    .get("reason", "unknown")
                )
                if reason == "quotaExceeded":
                    raise YouTubeAPIError(
                        "YouTube API quota exceeded (10K units/day). "
                        "Try again tomorrow or use a different API key."
                    )
                raise YouTubeAPIError(f"YouTube API 403: {reason}")

            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                all_videos.append({
                    "video_id": item.get("id", {}).get("videoId", ""),
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "channel_title": snippet.get("channelTitle", ""),
                })

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return all_videos

    def get_video_details(
        self,
        video_ids: list[str],
        batch_size: int = 50,
    ) -> dict[str, dict[str, Any]]:
        """Fetch full video snippets via videos.list (1 unit per 50 IDs).

        Args:
            video_ids: List of YouTube video IDs.
            batch_size: Max IDs per API call (YouTube max 50).

        Returns:
            Dict mapping video_id → {description, tags, ...} with full metadata.
        """
        details: dict[str, dict[str, Any]] = {}

        for i in range(0, len(video_ids), batch_size):
            batch = video_ids[i : i + batch_size]
            params: dict[str, Any] = {
                "key": self.api_key,
                "part": "snippet",
                "id": ",".join(batch),
            }

            resp = self.session.get(
                f"{self.BASE_URL}/videos", params=params, timeout=30
            )

            if resp.status_code == 403:
                error_data = resp.json()
                reason = (
                    error_data.get("error", {})
                    .get("errors", [{}])[0]
                    .get("reason", "unknown")
                )
                if reason == "quotaExceeded":
                    raise YouTubeAPIError(
                        "YouTube API quota exceeded (10K units/day). "
                        "Try again tomorrow or use a different API key."
                    )
                raise YouTubeAPIError(f"YouTube API 403: {reason}")

            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                vid = item.get("id", "")
                snippet = item.get("snippet", {})
                details[vid] = {
                    "description": snippet.get("description", ""),
                    "tags": snippet.get("tags", []),
                    "channel_title": snippet.get("channelTitle", ""),
                    "category_id": snippet.get("categoryId", ""),
                }

        return details


def test_youtube_connection() -> bool:
    """Test YouTube API connection with a minimal search."""
    try:
        collector = YouTubeCollector()
        videos = collector.search("성수동", days=7, max_results=1)
        print(f"✓ YouTube API connection successful")
        if videos:
            print(f"  Sample: {videos[0]['title'][:60]}...")
        return True
    except YouTubeAPIError as e:
        print(f"✗ YouTube API error: {e}")
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


if __name__ == "__main__":
    test_youtube_connection()
