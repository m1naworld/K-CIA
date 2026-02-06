"""점포 데이터 수집 및 적재 ETL.

소상공인시장진흥공단 상가정보 API로 성수동 4개 동 점포를 수집하고
좌표 검증 후 H3 인덱스를 생성하여 raw_semas_store 테이블에 적재.

Usage:
    python -m etl.load_semas_stores
    python -m etl.load_semas_stores --test  # 테스트 (동별 10건)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

import h3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from etl.config import DATABASE_URL
from etl.collectors.semas_api_collector import SemasAPICollector, SemasAPIError


# H3 해상도: 프로젝트 표준 res=10
H3_RESOLUTION = 10

# 서울 좌표 범위 (좌표 검증용)
SEOUL_LNG_MIN, SEOUL_LNG_MAX = 126.5, 127.5
SEOUL_LAT_MIN, SEOUL_LAT_MAX = 37.0, 38.0


def validate_coordinate(lng: float | None, lat: float | None) -> bool:
    """좌표가 서울 범위 내인지 검증.

    Args:
        lng: 경도
        lat: 위도

    Returns:
        유효 여부
    """
    if lng is None or lat is None:
        return False
    return (
        SEOUL_LNG_MIN <= lng <= SEOUL_LNG_MAX
        and SEOUL_LAT_MIN <= lat <= SEOUL_LAT_MAX
    )


def coord_to_h3(lat: float, lng: float, resolution: int = H3_RESOLUTION) -> str:
    """좌표를 H3 인덱스로 변환.

    Args:
        lat: 위도
        lng: 경도
        resolution: H3 해상도 (기본 9)

    Returns:
        H3 인덱스 문자열
    """
    return h3.geo_to_h3(lat, lng, resolution)


def load_stores(test_mode: bool = False) -> dict[str, int]:
    """점포 데이터 수집 및 적재.

    Args:
        test_mode: True이면 동별 10건만 수집 (테스트용)

    Returns:
        수집/적재 통계 딕셔너리
    """
    stats = {
        "fetched": 0,
        "valid_coords": 0,
        "invalid_coords": 0,
        "inserted": 0,
        "updated": 0,
        "errors": 0,
    }

    print("=" * 60)
    print("점포 데이터 수집 및 적재 시작")
    print(f"Test mode: {test_mode}")
    print(f"H3 Resolution: {H3_RESOLUTION}")
    print("=" * 60)

    # 1. API 수집
    try:
        collector = SemasAPICollector()
        max_per_dong = 10 if test_mode else None
        raw_stores = collector.fetch_all_seongsu(max_records_per_dong=max_per_dong)
        stats["fetched"] = len(raw_stores)
    except SemasAPIError as e:
        print(f"✗ API 수집 실패: {e}")
        return stats

    print(f"\n수집 완료: {stats['fetched']:,} 건")

    # 2. 좌표 검증 및 H3 변환
    processed_stores = []
    for raw in raw_stores:
        parsed = SemasAPICollector.parse_store(raw)

        lng = parsed.get("lng")
        lat = parsed.get("lat")

        if validate_coordinate(lng, lat):
            parsed["h3_index"] = coord_to_h3(lat, lng)
            processed_stores.append(parsed)
            stats["valid_coords"] += 1
        else:
            stats["invalid_coords"] += 1

    print(f"좌표 검증: 유효 {stats['valid_coords']:,}, 무효 {stats['invalid_coords']:,}")

    if not processed_stores:
        print("✗ 적재할 데이터 없음")
        return stats

    # 3. DB 적재
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)

    upsert_sql = text("""
        INSERT INTO raw_semas_store (
            store_id, store_name, branch_name,
            inds_l_cd, inds_l_nm, inds_m_cd, inds_m_nm, inds_s_cd, inds_s_nm,
            addr_road, lng, lat, h3_index, adong_cd, fetched_at
        ) VALUES (
            :store_id, :store_name, :branch_name,
            :inds_l_cd, :inds_l_nm, :inds_m_cd, :inds_m_nm, :inds_s_cd, :inds_s_nm,
            :addr_road, :lng, :lat, :h3_index, :adong_cd, :fetched_at
        )
        ON CONFLICT (store_id) DO UPDATE SET
            store_name = EXCLUDED.store_name,
            branch_name = EXCLUDED.branch_name,
            inds_l_cd = EXCLUDED.inds_l_cd,
            inds_l_nm = EXCLUDED.inds_l_nm,
            inds_m_cd = EXCLUDED.inds_m_cd,
            inds_m_nm = EXCLUDED.inds_m_nm,
            inds_s_cd = EXCLUDED.inds_s_cd,
            inds_s_nm = EXCLUDED.inds_s_nm,
            addr_road = EXCLUDED.addr_road,
            lng = EXCLUDED.lng,
            lat = EXCLUDED.lat,
            h3_index = EXCLUDED.h3_index,
            adong_cd = EXCLUDED.adong_cd,
            fetched_at = EXCLUDED.fetched_at
    """)

    now = datetime.utcnow()

    with Session() as session:
        for store in processed_stores:
            try:
                store["fetched_at"] = now
                result = session.execute(upsert_sql, store)

                # rowcount로 insert/update 구분 (PostgreSQL에서 항상 1)
                if result.rowcount > 0:
                    stats["inserted"] += 1

            except Exception as e:
                stats["errors"] += 1
                print(f"  Error inserting {store.get('store_id')}: {e}")

        session.commit()

    print(f"\nDB 적재 완료: {stats['inserted']:,} 건")

    # 4. 검증 쿼리 실행
    with Session() as session:
        # 동별 점포 수
        dong_counts = session.execute(text("""
            SELECT adong_cd, COUNT(*) as cnt
            FROM raw_semas_store
            GROUP BY adong_cd
            ORDER BY adong_cd
        """)).fetchall()

        print("\n동별 점포 수:")
        for row in dong_counts:
            print(f"  {row.adong_cd}: {row.cnt:,}")

        # H3 coverage
        h3_count = session.execute(text("""
            SELECT COUNT(DISTINCT h3_index) as cnt FROM raw_semas_store
        """)).scalar()
        print(f"\nH3 coverage: {h3_count:,} unique H3 cells")

    print("\n" + "=" * 60)
    print("점포 데이터 수집 완료")
    print(f"통계: {stats}")
    print("=" * 60)

    return stats


def main():
    parser = argparse.ArgumentParser(description="점포 데이터 수집 및 적재")
    parser.add_argument("--test", action="store_true", help="테스트 모드 (동별 10건)")
    args = parser.parse_args()

    stats = load_stores(test_mode=args.test)

    # 실패 시 exit code 1
    if stats["fetched"] == 0 or stats["inserted"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
