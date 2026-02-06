"""Sales data processor for D1 (추정매출-상권).

Parses CSV, filters Seongsu-dong commercial areas, upserts to fact_sales_area_qtr.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import pandas as pd

from etl.config import CSV_ENCODINGS, D1_COLUMN_MAPPING
from etl.db import execute_sql, get_engine

if TYPE_CHECKING:
    from collections.abc import Sequence


def read_csv_with_encoding(
    file_obj: io.BytesIO,
    encodings: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Try reading CSV with multiple encodings until one succeeds."""
    if encodings is None:
        encodings = CSV_ENCODINGS

    last_error = None
    for encoding in encodings:
        try:
            file_obj.seek(0)
            return pd.read_csv(file_obj, encoding=encoding, low_memory=False)
        except (UnicodeDecodeError, pd.errors.ParserError) as e:
            last_error = e
            continue

    raise ValueError(f"Failed to decode CSV with encodings {encodings}") from last_error


def get_seongsu_commercial_codes() -> set[str]:
    """Get commercial area codes from dim_area for Seongsu-dong."""
    result = execute_sql(
        "SELECT area_code FROM dim_area WHERE area_type = 'COMMERCIAL_AREA'"
    )
    return {str(row[0]) for row in result}


def filter_seongsu_sales(df: pd.DataFrame, commercial_codes: set[str]) -> pd.DataFrame:
    """Filter sales data to Seongsu-dong commercial areas only."""
    code_col = None
    for candidate in ["상권_코드", "TRDAR_CD", "commercial_code"]:
        if candidate in df.columns:
            code_col = candidate
            break

    if code_col is None:
        raise ValueError(f"Cannot find commercial code column. Available: {list(df.columns)}")

    df[code_col] = df[code_col].astype(str)
    return df[df[code_col].isin(commercial_codes)].copy()


def upsert_dim_category(df: pd.DataFrame) -> dict[str, int]:
    """Upsert unique service categories to dim_category. Returns code->cat_id mapping."""
    service_code_col = None
    service_name_col = None

    for candidate in ["서비스_업종_코드", "SERVICE_CODE"]:
        if candidate in df.columns:
            service_code_col = candidate
            break

    for candidate in ["서비스_업종_코드_명", "SERVICE_NAME"]:
        if candidate in df.columns:
            service_name_col = candidate
            break

    if service_code_col is None or service_name_col is None:
        raise ValueError(f"Cannot find service code/name columns. Available: {list(df.columns)}")

    unique_categories = df[[service_code_col, service_name_col]].drop_duplicates()

    for _, row in unique_categories.iterrows():
        code = str(row[service_code_col])
        name = str(row[service_name_col])
        execute_sql(
            """
            INSERT INTO dim_category (service_code, service_name)
            VALUES (:code, :name)
            ON CONFLICT (service_code) DO UPDATE SET service_name = EXCLUDED.service_name
            """,
            {"code": code, "name": name},
        )

    result = execute_sql("SELECT service_code, cat_id FROM dim_category")
    return {str(row[0]): row[1] for row in result}


def get_area_id_mapping() -> dict[str, int]:
    """Get commercial area code to area_id mapping."""
    result = execute_sql(
        "SELECT area_code, area_id FROM dim_area WHERE area_type = 'COMMERCIAL_AREA'"
    )
    return {str(row[0]): row[1] for row in result}


def upsert_fact_sales(df: pd.DataFrame, cat_mapping: dict[str, int], area_mapping: dict[str, int]) -> int:
    """Upsert sales data to fact_sales_area_qtr. Returns row count."""
    qtr_col = None
    code_col = None
    service_col = None
    sales_amt_col = None
    sales_cnt_col = None

    for candidate in ["기준_년분기_코드", "QTR_CODE"]:
        if candidate in df.columns:
            qtr_col = candidate
            break

    for candidate in ["상권_코드", "TRDAR_CD"]:
        if candidate in df.columns:
            code_col = candidate
            break

    for candidate in ["서비스_업종_코드", "SERVICE_CODE"]:
        if candidate in df.columns:
            service_col = candidate
            break

    for candidate in ["당월_매출_금액", "분기당_매출_금액", "THSMON_SELNG_AMT"]:
        if candidate in df.columns:
            sales_amt_col = candidate
            break

    for candidate in ["당월_매출_건수", "분기당_매출_건수", "THSMON_SELNG_CO"]:
        if candidate in df.columns:
            sales_cnt_col = candidate
            break

    if not all([qtr_col, code_col, service_col]):
        raise ValueError(f"Missing required columns. Available: {list(df.columns)}")

    upserted = 0
    for _, row in df.iterrows():
        area_code = str(row[code_col])
        service_code = str(row[service_col])

        area_id = area_mapping.get(area_code)
        cat_id = cat_mapping.get(service_code)

        if area_id is None or cat_id is None:
            continue

        qtr = str(row[qtr_col])
        sales_amt = int(row[sales_amt_col]) if sales_amt_col and pd.notna(row[sales_amt_col]) else None
        sales_cnt = int(row[sales_cnt_col]) if sales_cnt_col and pd.notna(row[sales_cnt_col]) else None

        execute_sql(
            """
            INSERT INTO fact_sales_area_qtr (area_id, qtr, cat_id, sales_amt, sales_cnt)
            VALUES (:area_id, :qtr, :cat_id, :sales_amt, :sales_cnt)
            ON CONFLICT (area_id, qtr, cat_id) DO UPDATE SET
                sales_amt = EXCLUDED.sales_amt,
                sales_cnt = EXCLUDED.sales_cnt
            """,
            {
                "area_id": area_id,
                "qtr": qtr,
                "cat_id": cat_id,
                "sales_amt": sales_amt,
                "sales_cnt": sales_cnt,
            },
        )
        upserted += 1

    return upserted


def process_sales_csv(file_obj: io.BytesIO, filename: str = "") -> dict:
    """Process a single sales CSV file. Returns stats dict."""
    print(f"  Reading CSV: {filename}")
    df = read_csv_with_encoding(file_obj)
    print(f"    Total rows: {len(df)}")
    print(f"    Columns: {list(df.columns)[:10]}...")

    commercial_codes = get_seongsu_commercial_codes()
    print(f"    Seongsu commercial codes: {len(commercial_codes)}")

    df_filtered = filter_seongsu_sales(df, commercial_codes)
    print(f"    Filtered rows (Seongsu): {len(df_filtered)}")

    if len(df_filtered) == 0:
        return {"filename": filename, "total": len(df), "filtered": 0, "upserted": 0}

    cat_mapping = upsert_dim_category(df_filtered)
    print(f"    Categories: {len(cat_mapping)}")

    area_mapping = get_area_id_mapping()
    upserted = upsert_fact_sales(df_filtered, cat_mapping, area_mapping)
    print(f"    Upserted: {upserted}")

    return {
        "filename": filename,
        "total": len(df),
        "filtered": len(df_filtered),
        "upserted": upserted,
    }
