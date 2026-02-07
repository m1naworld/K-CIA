"""Load D14 (실거래가) via data.go.kr API → fact_real_price.

데이터셋: data.go.kr 15126463 (국토부 상업용 부동산 임대차 정보)
*** API KEY 필요: REALPRICE_API_KEY (data.go.kr 공공데이터포털 발급) ***

Usage:
    REALPRICE_API_KEY=... python -m etl.load_d14_realprice
    REALPRICE_API_KEY=... python -m etl.load_d14_realprice 202401 202412

Data Requirements:
    - API KEY: data.go.kr 에서 '국토부 상업용 부동산 임대차 정보' 활용 신청
    - URL: https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent
    - Parameters: LAWD_CD (법정동코드 5자리), DEAL_YMD (계약연월 YYYYMM)
    - 성동구 법정동코드: 11200
"""

from __future__ import annotations

import os
import sys
import time
import requests
from typing import Any

from etl.db import execute_sql

API_KEY = os.getenv("REALPRICE_API_KEY")
BASE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
LAWD_CD = "11200"  # 성동구


def fetch_real_price(deal_ymd: str) -> list[dict[str, Any]]:
    """Fetch real estate transaction data for a month."""
    if not API_KEY:
        raise RuntimeError(
            "REALPRICE_API_KEY 환경변수가 설정되지 않았습니다. "
            "data.go.kr에서 API 키를 발급받아 설정해주세요."
        )

    params = {
        "serviceKey": API_KEY,
        "LAWD_CD": LAWD_CD,
        "DEAL_YMD": deal_ymd,
        "pageNo": 1,
        "numOfRows": 1000,
    }

    results = []
    while True:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        body = data.get("response", {}).get("body", {})
        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]

        results.extend(items)

        total = int(body.get("totalCount", 0))
        if len(results) >= total:
            break
        params["pageNo"] += 1
        time.sleep(0.5)

    return results


def upsert_real_price(rows: list[dict[str, Any]]) -> int:
    """Upsert real price data. Filters to Seongsu-dong areas."""
    upserted = 0
    seongsu_dongs = {"성수동1가", "성수동2가"}

    for row in rows:
        dong = row.get("umdNm", "")
        if dong not in seongsu_dongs:
            continue

        # Find area_id by matching
        result = execute_sql(
            """
            SELECT area_id FROM dim_area
            WHERE area_type = 'ADMIN_DONG'
            AND area_name LIKE :pattern
            LIMIT 1
            """,
            {"pattern": f"%{dong[:3]}%"},
        )
        area_row = result.fetchone()
        if area_row is None:
            continue
        area_id = area_row[0]

        deal_year = row.get("dealYear", "")
        deal_month = str(row.get("dealMonth", "")).zfill(2)
        contract_ym = f"{deal_year}{deal_month}"

        deposit = float(row.get("deposit", 0) or 0)
        monthly_rent = float(row.get("monthlyRent", 0) or 0)
        area = float(row.get("excluUseAr", 0) or 0)
        floor_val = row.get("floor", None)
        build_year = row.get("buildYear", None)

        price_per_sqm = (deposit + monthly_rent * 12) / area if area > 0 else None
        building_age = int(deal_year) - int(build_year) if build_year else None

        execute_sql(
            """
            INSERT INTO fact_real_price (area_id, contract_ym, price_per_sqm, floor, building_age)
            VALUES (:area_id, :contract_ym, :price_per_sqm, :floor, :building_age)
            ON CONFLICT DO NOTHING
            """,
            {
                "area_id": area_id,
                "contract_ym": contract_ym,
                "price_per_sqm": price_per_sqm,
                "floor": int(floor_val) if floor_val else None,
                "building_age": building_age,
            },
        )
        upserted += 1

    return upserted


def main(months: list[str] | None = None):
    """Main ETL for D14 real price data."""
    if not API_KEY:
        print("[D14] ERROR: REALPRICE_API_KEY 환경변수가 필요합니다.")
        print("[D14] data.go.kr에서 '국토부 상업용 부동산 임대차 정보' 활용 신청 후 발급")
        return

    if months is None:
        # Default: recent 12 months
        import datetime
        today = datetime.date.today()
        months = []
        for i in range(12):
            d = today.replace(day=1) - datetime.timedelta(days=30 * i)
            months.append(d.strftime("%Y%m"))

    total_upserted = 0
    for ym in months:
        print(f"[D14] Fetching {ym}...")
        try:
            rows = fetch_real_price(ym)
            print(f"[D14]   → {len(rows)} rows fetched")
            upserted = upsert_real_price(rows)
            total_upserted += upserted
            print(f"[D14]   → {upserted} records upserted")
        except Exception as e:
            print(f"[D14]   → Error: {e}")
        time.sleep(1)

    print(f"[D14] Done. Total upserted: {total_upserted}")


if __name__ == "__main__":
    ms = sys.argv[1:] if len(sys.argv) > 1 else None
    main(ms)
