"""Load D8 (집객시설-상권배후지) via Seoul Open API → fact_facilities_area.

D8 데이터셋: OA-15581 (서울시 우리마을가게 상권분석서비스-집객시설)
Uses existing SEOUL_API_KEY.

Usage:
    python -m etl.load_d8_facilities
    python -m etl.load_d8_facilities 20244
"""

from __future__ import annotations

import sys
from typing import Any

from etl.collectors.seoul_api_collector import SeoulAPICollector, API_SERVICES
from etl.db import execute_sql


TARGET_QUARTERS = ["20244", "20243", "20242", "20241"]

# D8 API service key in Seoul OpenAPI
D8_SERVICE = "VwsmTrdarFlpopQq"  # 집객시설


def get_commercial_area_mapping() -> dict[str, int]:
    """Get commercial area code to area_id mapping."""
    result = execute_sql(
        "SELECT area_code, area_id FROM dim_area WHERE area_type = 'COMMERCIAL_AREA'"
    )
    return {str(row[0]): row[1] for row in result}


# Facility type mapping from API columns
FACILITY_COLUMNS = {
    "VIATR_FCLTY_CO": "관광시설",
    "DRTS_FCLTY_CO": "교통시설",
    "PBLOFC_CO": "공공기관",
    "BANK_CO": "은행",
    "GERNL_HSPTL_CO": "종합병원",
    "PARMACY_CO": "약국",
    "KNDRGR_CO": "유치원",
    "ELESCH_CO": "초등학교",
    "MSKUL_CO": "중학교",
    "HGSCHL_CO": "고등학교",
    "UNIV_CO": "대학교",
    "DPSTR_CO": "백화점",
    "LCMRT_CO": "대형마트",
    "THEAT_CO": "영화관",
    "STAYNG_FCLTY_CO": "숙박시설",
    "ARPRT_CO": "공항",
    "RLROAD_STATN_CO": "철도역",
    "BUS_TRMNL_CO": "버스터미널",
    "SUBWAY_STATN_CO": "지하철역",
    "BUS_STOPPNT_CO": "버스정류장",
}


def upsert_facilities(
    rows: list[dict[str, Any]],
    area_mapping: dict[str, int],
) -> int:
    """Upsert facility data to fact_facilities_area."""
    upserted = 0

    for row in rows:
        commercial_code = str(row.get("TRDAR_CD", ""))
        area_id = area_mapping.get(commercial_code)
        if area_id is None:
            continue

        qtr = str(row.get("STDR_YR_QTR_CD", ""))
        if not qtr:
            continue

        for col, facility_type in FACILITY_COLUMNS.items():
            count = row.get(col)
            if count is None:
                continue
            try:
                facility_cnt = int(count)
            except (ValueError, TypeError):
                continue

            if facility_cnt == 0:
                continue

            execute_sql(
                """
                INSERT INTO fact_facilities_area (area_id, qtr, facility_type, facility_cnt)
                VALUES (:area_id, :qtr, :facility_type, :facility_cnt)
                ON CONFLICT (area_id, qtr, facility_type)
                DO UPDATE SET facility_cnt = :facility_cnt
                """,
                {
                    "area_id": area_id,
                    "qtr": qtr,
                    "facility_type": facility_type,
                    "facility_cnt": facility_cnt,
                },
            )
            upserted += 1

    return upserted


def main(quarters: list[str] | None = None):
    """Main ETL entry point for D8 facilities."""
    if quarters is None:
        quarters = TARGET_QUARTERS

    area_mapping = get_commercial_area_mapping()
    print(f"[D8] Commercial areas loaded: {len(area_mapping)}")

    collector = SeoulAPICollector()
    total_upserted = 0

    for qtr in quarters:
        print(f"[D8] Fetching quarter {qtr}...")
        try:
            rows = collector.fetch_all(
                service_name=D8_SERVICE,
                extra_params={"STDR_YR_QTR_CD": qtr},
            )
            print(f"[D8]   → {len(rows)} rows fetched")
            upserted = upsert_facilities(rows, area_mapping)
            total_upserted += upserted
            print(f"[D8]   → {upserted} facility records upserted")
        except Exception as e:
            print(f"[D8]   → Error: {e}")

    print(f"[D8] Done. Total upserted: {total_upserted}")


if __name__ == "__main__":
    qtrs = sys.argv[1:] if len(sys.argv) > 1 else None
    main(qtrs)
