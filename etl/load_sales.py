"""Main script: Load D1 (추정매출-상권) → dim_category + fact_sales_area_qtr.

Usage:
    python -m etl.load_sales

Expects CSV or ZIP files in data/raw/d1_sales/ directory.
Download from: https://data.seoul.go.kr/dataList/OA-15572/S/1/datasetView.do
"""

import io
import re
import sys
from pathlib import Path

from etl.collectors.seoul_zip_collector import (
    extract_csvs_from_zip,
    extract_year_from_filename,
    find_local_zips,
)
from etl.config import D1_DIR, D1_YEARS
from etl.db import execute_sql
from etl.processors.sales_processor import process_sales_csv


def find_local_csvs(directory: Path) -> list[Path]:
    """Find CSV files in directory."""
    if not directory.exists():
        return []
    return sorted(directory.glob("*.csv"), reverse=True)


def extract_year_from_csv_filename(filename: str) -> int | None:
    """Extract year from CSV filename."""
    match = re.search(r"(\d{4})년?\.csv", filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def main() -> None:
    print("=" * 60)
    print("M1-4: Load D1 (추정매출) → fact_sales_area_qtr")
    print("=" * 60)

    if not D1_DIR.exists():
        D1_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\n[INFO] Created directory: {D1_DIR}")

    zip_files = find_local_zips(D1_DIR)
    csv_files = find_local_csvs(D1_DIR)

    if not zip_files and not csv_files:
        print(f"\n[ERROR] No CSV or ZIP files found in {D1_DIR}")
        print("\n다운로드 방법:")
        print("  1. https://data.seoul.go.kr/dataList/OA-15572/S/1/datasetView.do 접속")
        print("  2. '서울시 상권분석서비스(추정매출-상권)_2024년.zip' 등 다운로드")
        print(f"  3. {D1_DIR}/ 폴더에 파일 복사")
        print("  4. 다시 실행: python -m etl.load_sales")
        sys.exit(1)

    total_stats = {"files": 0, "total_rows": 0, "filtered_rows": 0, "upserted": 0}

    if csv_files:
        print(f"\n[Step 1] Found {len(csv_files)} CSV file(s):")
        for cf in csv_files:
            year = extract_year_from_csv_filename(cf.name)
            print(f"  - {cf.name} (year: {year})")

        for csv_path in csv_files:
            year = extract_year_from_csv_filename(csv_path.name)
            if year and year not in D1_YEARS:
                print(f"\n[SKIP] {csv_path.name} - year {year} not in target years {D1_YEARS}")
                continue

            print(f"\n[Step 2] Processing: {csv_path.name}")
            with open(csv_path, "rb") as f:
                csv_bytes = io.BytesIO(f.read())
            stats = process_sales_csv(csv_bytes, csv_path.name)
            total_stats["files"] += 1
            total_stats["total_rows"] += stats["total"]
            total_stats["filtered_rows"] += stats["filtered"]
            total_stats["upserted"] += stats["upserted"]

    elif zip_files:
        print(f"\n[Step 1] Found {len(zip_files)} ZIP file(s):")
        for zf in zip_files:
            year = extract_year_from_filename(zf.name)
            print(f"  - {zf.name} (year: {year})")

        for zip_path in zip_files:
            year = extract_year_from_filename(zip_path.name)
            if year and year not in D1_YEARS:
                print(f"\n[SKIP] {zip_path.name} - year {year} not in target years {D1_YEARS}")
                continue

            print(f"\n[Step 2] Processing: {zip_path.name}")

            for csv_name, csv_bytes in extract_csvs_from_zip(zip_path):
                stats = process_sales_csv(csv_bytes, csv_name)
                total_stats["files"] += 1
                total_stats["total_rows"] += stats["total"]
                total_stats["filtered_rows"] += stats["filtered"]
                total_stats["upserted"] += stats["upserted"]

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Files processed:     {total_stats['files']}")
    print(f"  Total rows read:     {total_stats['total_rows']:,}")
    print(f"  Seongsu rows:        {total_stats['filtered_rows']:,}")
    print(f"  Rows upserted:       {total_stats['upserted']:,}")

    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    result = execute_sql("SELECT count(*) FROM fact_sales_area_qtr")
    count = list(result)[0][0]
    print(f"  fact_sales_area_qtr: {count} rows")

    result = execute_sql("SELECT count(*) FROM dim_category")
    cat_count = list(result)[0][0]
    print(f"  dim_category: {cat_count} rows")

    result = execute_sql(
        """
        SELECT qtr, count(*) as cnt
        FROM fact_sales_area_qtr
        GROUP BY qtr
        ORDER BY qtr DESC
        LIMIT 8
        """
    )
    print("\n  Quarters coverage:")
    for row in result:
        print(f"    {row[0]}: {row[1]} rows")

    result = execute_sql(
        """
        SELECT dc.service_name, count(*) as cnt, sum(f.sales_amt) as total_sales
        FROM fact_sales_area_qtr f
        JOIN dim_category dc ON f.cat_id = dc.cat_id
        GROUP BY dc.service_name
        ORDER BY total_sales DESC NULLS LAST
        LIMIT 10
        """
    )
    print("\n  Top 10 categories by sales:")
    for row in result:
        sales = f"{row[2]:,}" if row[2] else "N/A"
        print(f"    {row[0]}: {row[1]} rows, {sales} won")

    if count > 0:
        print("\n✓ Done! DoD: fact_sales_area_qtr > 0 ✓")
    else:
        print("\n✗ Warning: No data loaded. Check ZIP files.")


if __name__ == "__main__":
    main()
