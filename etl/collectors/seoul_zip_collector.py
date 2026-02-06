"""Seoul Open Data Portal ZIP file collector.

Downloads ZIP files from data.seoul.go.kr for datasets like D1 (추정매출).
Handles both automatic discovery and manual file placement.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from collections.abc import Iterator

SEOUL_DATA_BASE_URL = "https://data.seoul.go.kr"
REQUEST_TIMEOUT = 120
CHUNK_SIZE = 8192


def discover_zip_urls(dataset_id: str, page_url: str | None = None) -> list[dict]:
    """Discover available ZIP file download URLs from Seoul Open Data Portal.

    Note: Seoul Open Data uses dynamic JavaScript-based download links.
    This function attempts to parse the page, but may require Playwright
    for full automation. Returns empty list if discovery fails.
    """
    if page_url is None:
        page_url = f"{SEOUL_DATA_BASE_URL}/dataList/{dataset_id}/S/1/datasetView.do"

    try:
        resp = requests.get(page_url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    zip_pattern = re.compile(
        r"서울시[_\s]*상권분석서비스\(추정매출-상권\)[_\s]*(\d{4})년\.zip",
        re.IGNORECASE,
    )

    files = []
    for match in zip_pattern.finditer(resp.text):
        year = int(match.group(1))
        files.append({
            "year": year,
            "filename": match.group(0),
        })

    return sorted(files, key=lambda x: x["year"], reverse=True)


def download_zip(url: str, dest_path: Path) -> Path:
    """Download a ZIP file from URL to destination path."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    resp = requests.get(url, timeout=REQUEST_TIMEOUT, stream=True)
    resp.raise_for_status()

    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
            f.write(chunk)

    return dest_path


def find_local_zips(directory: Path) -> list[Path]:
    """Find all ZIP files in directory (for manual download workflow)."""
    if not directory.exists():
        return []
    return sorted(directory.glob("*.zip"), reverse=True)


def extract_csvs_from_zip(zip_path: Path) -> Iterator[tuple[str, io.BytesIO]]:
    """Extract CSV files from a ZIP archive.

    Yields (filename, BytesIO) tuples for each CSV found.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.lower().endswith(".csv"):
                with zf.open(name) as f:
                    yield name, io.BytesIO(f.read())


def extract_year_from_filename(filename: str) -> int | None:
    """Extract year from filename like '서울시 상권분석서비스(추정매출-상권)_2024년.zip'."""
    match = re.search(r"(\d{4})년?\.zip", filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None
