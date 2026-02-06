"""ETL configuration: paths, CRS constants, Seongsu-dong filters."""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
D9_DIR = DATA_RAW / "d9_admin_dong"
D3_DIR = DATA_RAW / "d3_commercial_area"

# ── CRS ────────────────────────────────────────────────────────
CRS_WGS84 = "EPSG:4326"
CRS_KOREA = "EPSG:5181"  # D3 상권영역 좌표계

# ── 성수동 행정동 필터 ─────────────────────────────────────────
# 성수동 4개 행정동 (성동구)
SEONGSU_DONG_NAMES: list[str] = [
    "성수1가1동",
    "성수1가2동",
    "성수2가1동",
    "성수2가3동",
]

# 행정동코드 (10자리) — SHP에 코드가 있을 경우 사용
SEONGSU_DONG_CODES: list[str] = [
    "1120065000",  # 성수1가1동
    "1120066000",  # 성수1가2동
    "1120067000",  # 성수2가1동
    "1120069000",  # 성수2가3동
]

# 행정동코드 (8자리) — API ADSTRD_CD 필터용
SEONGSU_ADSTRD_CODES: list[str] = [
    "11200650",  # 성수1가1동
    "11200660",  # 성수1가2동
    "11200670",  # 성수2가1동
    "11200690",  # 성수2가3동
]

# 행정동명 매칭에 사용할 SHP 컬럼 후보 (우선순위 순)
DONG_NAME_CANDIDATES = ["ADM_DR_NM", "ADM_NM", "adm_nm", "EMD_NM", "행정동명", "dong_nm"]
DONG_CODE_CANDIDATES = ["ADM_DR_CD", "ADM_CD", "adm_cd", "EMD_CD", "행정동코드"]

# 상권코드 컬럼 후보
COMMERCIAL_CODE_CANDIDATES = ["TRDAR_CD", "상권_코드", "TRDAREA_CD", "TRDAR_CD"]
COMMERCIAL_NAME_CANDIDATES = ["TRDAR_CD_NM", "TRDAR_NM", "TRDAR_CD_N", "상권_코드_명", "TRDAREA_NM"]

# ── D1 매출 데이터 설정 ────────────────────────────────────────
D1_DIR = DATA_RAW / "d1_sales"
D1_DATASET_ID = "OA-15572"
D1_YEARS = [2024, 2023, 2022]  # 최근 3년 (8분기 커버)

# D1 CSV 컬럼 매핑 (서울시 상권분석서비스 추정매출-상권)
D1_COLUMN_MAPPING = {
    "기준_년분기_코드": "qtr_code",
    "상권_코드": "commercial_code",
    "상권_코드_명": "commercial_name",
    "서비스_업종_코드": "service_code",
    "서비스_업종_코드_명": "service_name",
    "당월_매출_금액": "monthly_sales",
    "당월_매출_건수": "monthly_count",
    "분기당_매출_금액": "quarterly_sales",
    "분기당_매출_건수": "quarterly_count",
}

# CSV 인코딩 후보 (순서대로 시도)
CSV_ENCODINGS = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]

# ── DB ─────────────────────────────────────────────────────────
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://kcia:kcia_local_pw@localhost:5432/kcia",
)

# ── 소상공인 상가정보 API ────────────────────────────────────
SEMAS_API_KEY = os.getenv("SEMAS_API_KEY")
SEMAS_API_BASE_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2"
