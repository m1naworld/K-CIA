"""Load D15 (임대료/공실률) from CSV download → fact_rent_vacancy.

데이터셋: 서울 열린데이터광장 OA-12553 (서울시 상권분석서비스-임대)
*** CSV 파일 수동 다운로드 필요 (API 키 불필요) ***

Download URL: https://data.seoul.go.kr/dataList/OA-12553/F/1/datasetView.do
파일 위치: data/raw/d15_rent/ 디렉토리에 CSV 파일 배치

Usage:
    python -m etl.load_d15_rent
    python -m etl.load_d15_rent data/raw/d15_rent/rent_data.csv
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

from etl.config import CSV_ENCODINGS, DATA_RAW
from etl.db import execute_sql

D15_DIR = DATA_RAW / "d15_rent"


def read_csv_with_encoding(filepath: Path) -> pd.DataFrame:
    """Try multiple encodings to read CSV."""
    for enc in CSV_ENCODINGS:
        try:
            return pd.read_csv(filepath, encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Could not read {filepath} with any encoding")


def get_area_mapping() -> dict[str, int]:
    """Get commercial area code to area_id mapping."""
    result = execute_sql(
        "SELECT area_code, area_id FROM dim_area WHERE area_type = 'COMMERCIAL_AREA'"
    )
    return {str(row[0]): row[1] for row in result}


def upsert_rent_data(df: pd.DataFrame, area_mapping: dict[str, int]) -> int:
    """Upsert rent/vacancy data from DataFrame."""
    upserted = 0

    # Expected columns (Korean names from Seoul OpenData)
    code_col = None
    qtr_col = None
    rent_col = None
    vacancy_col = None

    for col in df.columns:
        if "상권" in col and "코드" in col and "명" not in col:
            code_col = col
        elif "년분기" in col or "기준" in col:
            qtr_col = col
        elif "임대" in col and "료" in col:
            rent_col = col
        elif "공실" in col and "률" in col:
            vacancy_col = col

    if code_col is None:
        print("[D15] WARNING: 상권코드 컬럼을 찾을 수 없습니다")
        return 0

    for _, row in df.iterrows():
        commercial_code = str(row.get(code_col, "")).strip()
        area_id = area_mapping.get(commercial_code)
        if area_id is None:
            continue

        qtr = str(row.get(qtr_col, "")).strip() if qtr_col else ""
        if not qtr:
            continue

        rent_per_sqm = float(row[rent_col]) if rent_col and pd.notna(row.get(rent_col)) else None
        vacancy_rate = float(row[vacancy_col]) if vacancy_col and pd.notna(row.get(vacancy_col)) else None

        execute_sql(
            """
            INSERT INTO fact_rent_vacancy (area_id, qtr, rent_per_sqm, vacancy_rate)
            VALUES (:area_id, :qtr, :rent_per_sqm, :vacancy_rate)
            ON CONFLICT (area_id, qtr) DO UPDATE
            SET rent_per_sqm = COALESCE(:rent_per_sqm, fact_rent_vacancy.rent_per_sqm),
                vacancy_rate = COALESCE(:vacancy_rate, fact_rent_vacancy.vacancy_rate)
            """,
            {
                "area_id": area_id,
                "qtr": qtr,
                "rent_per_sqm": rent_per_sqm,
                "vacancy_rate": vacancy_rate,
            },
        )
        upserted += 1

    return upserted


def main(csv_path: str | None = None):
    """Main ETL for D15 rent/vacancy data."""
    area_mapping = get_area_mapping()
    print(f"[D15] Commercial areas loaded: {len(area_mapping)}")

    if csv_path:
        files = [Path(csv_path)]
    else:
        D15_DIR.mkdir(parents=True, exist_ok=True)
        files = list(D15_DIR.glob("*.csv"))

    if not files:
        print(f"[D15] CSV 파일이 없습니다.")
        print(f"[D15] 서울 열린데이터광장에서 OA-12553 데이터를 다운로드하여")
        print(f"[D15] {D15_DIR}/ 디렉토리에 배치해주세요.")
        print(f"[D15] URL: https://data.seoul.go.kr/dataList/OA-12553/F/1/datasetView.do")
        return

    total_upserted = 0
    for f in files:
        print(f"[D15] Processing {f.name}...")
        try:
            df = read_csv_with_encoding(f)
            print(f"[D15]   → {len(df)} rows in CSV")
            upserted = upsert_rent_data(df, area_mapping)
            total_upserted += upserted
            print(f"[D15]   → {upserted} records upserted")
        except Exception as e:
            print(f"[D15]   → Error: {e}")

    print(f"[D15] Done. Total upserted: {total_upserted}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    main(path)
