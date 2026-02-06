"""점포 수 기반 H3 Weight 계산 ETL.

기존 면적 기반 H3 매핑(bridge_area_h3_weight)의 H3 목록을 기준으로,
각 H3의 점포 수 비율로 weight를 재계산하여 bridge_area_h3_weight_store에 적재.

Weight = (해당 H3의 점포 수) / (상권 내 전체 점포 수)

Usage:
    python -m etl.compute_store_weight
"""

from __future__ import annotations

import sys
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from etl.config import DATABASE_URL


def compute_store_weights() -> dict[str, int]:
    """점포 수 기반 weight 계산 및 적재.

    Returns:
        계산 통계 딕셔너리
    """
    stats = {
        "areas_processed": 0,
        "areas_with_stores": 0,
        "areas_without_stores": 0,
        "h3_records": 0,
        "weight_sum_errors": 0,
    }

    print("=" * 60)
    print("점포 수 기반 H3 Weight 계산 시작")
    print("=" * 60)

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # 1. 전제 조건 확인
        area_h3_count = session.execute(
            text("SELECT COUNT(DISTINCT area_id) FROM bridge_area_h3_weight")
        ).scalar() or 0

        store_h3_count = session.execute(
            text("SELECT COUNT(*) FROM fact_store_h3_count")
        ).scalar() or 0

        print(f"면적 기반 H3 매핑 상권 수: {area_h3_count}")
        print(f"점포 H3 집계 레코드 수: {store_h3_count}")

        if area_h3_count == 0:
            print("✗ bridge_area_h3_weight에 데이터 없음. 먼저 H3 매핑을 실행하세요.")
            return stats

        if store_h3_count == 0:
            print("✗ fact_store_h3_count에 데이터 없음. 먼저 load_store_h3_count를 실행하세요.")
            return stats

        # 2. 상권별 처리
        # 각 상권(area_id)에 대해:
        # - 해당 상권의 H3 목록 조회 (면적 기반 매핑에서)
        # - 각 H3의 점포 수 조회
        # - 상권 전체 점포 수 계산
        # - weight = 각 H3 점포 수 / 전체 점포 수

        now = datetime.utcnow()

        # 기존 데이터 삭제 후 새로 적재 (TRUNCATE + INSERT)
        session.execute(text("DELETE FROM bridge_area_h3_weight_store"))

        # 상권별 H3 weight 계산 쿼리
        # CTE로 한 번에 계산하여 INSERT
        compute_sql = text("""
            WITH area_h3_store AS (
                -- 각 상권의 H3와 해당 H3의 점포 수
                SELECT
                    bw.area_id,
                    bw.h3_index,
                    COALESCE(sc.store_cnt, 0) as store_cnt
                FROM bridge_area_h3_weight bw
                LEFT JOIN fact_store_h3_count sc ON sc.h3_index = bw.h3_index
            ),
            area_total AS (
                -- 상권별 총 점포 수
                SELECT area_id, SUM(store_cnt) as total_cnt
                FROM area_h3_store
                GROUP BY area_id
            )
            INSERT INTO bridge_area_h3_weight_store (area_id, h3_index, store_cnt, weight, calculated_at)
            SELECT
                ahs.area_id,
                ahs.h3_index,
                ahs.store_cnt,
                CASE
                    WHEN at.total_cnt > 0 THEN ahs.store_cnt::numeric / at.total_cnt
                    ELSE 0  -- 점포가 없는 상권은 weight 0
                END as weight,
                :now
            FROM area_h3_store ahs
            JOIN area_total at ON at.area_id = ahs.area_id
        """)

        result = session.execute(compute_sql, {"now": now})
        session.commit()

        # 3. 결과 통계
        stats["h3_records"] = session.execute(
            text("SELECT COUNT(*) FROM bridge_area_h3_weight_store")
        ).scalar() or 0

        area_stats = session.execute(text("""
            SELECT
                COUNT(DISTINCT area_id) as total_areas,
                COUNT(DISTINCT CASE WHEN store_cnt > 0 THEN area_id END) as areas_with_stores
            FROM bridge_area_h3_weight_store
        """)).fetchone()

        stats["areas_processed"] = area_stats.total_areas or 0
        stats["areas_with_stores"] = area_stats.areas_with_stores or 0
        stats["areas_without_stores"] = stats["areas_processed"] - stats["areas_with_stores"]

        print(f"\nWeight 계산 완료:")
        print(f"  처리된 상권 수: {stats['areas_processed']}")
        print(f"  점포 있는 상권: {stats['areas_with_stores']}")
        print(f"  점포 없는 상권: {stats['areas_without_stores']} (면적 기반 fallback)")
        print(f"  H3 레코드 수: {stats['h3_records']:,}")

        # 4. Weight 합계 검증 (각 상권의 weight 합이 1이어야 함)
        weight_errors = session.execute(text("""
            SELECT area_id, SUM(weight) as total_weight
            FROM bridge_area_h3_weight_store
            GROUP BY area_id
            HAVING ABS(SUM(weight) - 1.0) > 0.01
                AND SUM(weight) > 0  -- 점포 없는 상권 제외
        """)).fetchall()

        stats["weight_sum_errors"] = len(weight_errors)

        if weight_errors:
            print(f"\n⚠ Weight 합계 오류 ({len(weight_errors)}건):")
            for row in weight_errors[:5]:
                print(f"  area_id={row.area_id}: sum={row.total_weight:.4f}")
        else:
            print("\n✓ Weight 합계 검증 통과 (모든 상권 sum=1.0)")

        # 5. 면적 vs 점포 weight 비교 (상위 차이)
        compare_sql = text("""
            SELECT
                da.area_name,
                bw.h3_index,
                bw.weight as area_weight,
                bs.weight as store_weight,
                ABS(bw.weight - bs.weight) as diff
            FROM bridge_area_h3_weight bw
            JOIN bridge_area_h3_weight_store bs
                ON bs.area_id = bw.area_id AND bs.h3_index = bw.h3_index
            JOIN dim_area da ON da.area_id = bw.area_id
            WHERE bs.store_cnt > 0  -- 점포 있는 H3만
            ORDER BY diff DESC
            LIMIT 10
        """)

        diff_rows = session.execute(compare_sql).fetchall()

        print("\n면적 vs 점포 weight 차이 상위 10:")
        for row in diff_rows:
            print(f"  {row.area_name[:15]:15} {row.h3_index}: "
                  f"면적={row.area_weight:.4f}, 점포={row.store_weight:.4f}, "
                  f"차이={row.diff:.4f}")

        # 6. 점포 수 0인 H3 통계
        zero_store_h3 = session.execute(text("""
            SELECT COUNT(*) FROM bridge_area_h3_weight_store WHERE store_cnt = 0
        """)).scalar() or 0

        total_h3 = session.execute(text("""
            SELECT COUNT(*) FROM bridge_area_h3_weight_store
        """)).scalar() or 0

        print(f"\n점포 없는 H3: {zero_store_h3:,} / {total_h3:,} "
              f"({100*zero_store_h3/total_h3:.1f}%)")

    print("\n" + "=" * 60)
    print("점포 수 기반 H3 Weight 계산 완료")
    print(f"통계: {stats}")
    print("=" * 60)

    return stats


def compare_weights_report() -> None:
    """면적 기반 vs 점포 기반 weight 비교 리포트 출력."""
    print("\n" + "=" * 60)
    print("면적 vs 점포 Weight 비교 리포트")
    print("=" * 60)

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # 상권별 요약
        summary_sql = text("""
            WITH comparison AS (
                SELECT
                    da.area_name,
                    bw.area_id,
                    COUNT(*) as h3_count,
                    SUM(CASE WHEN bs.store_cnt > 0 THEN 1 ELSE 0 END) as h3_with_stores,
                    AVG(ABS(bw.weight - bs.weight)) as avg_diff,
                    MAX(ABS(bw.weight - bs.weight)) as max_diff
                FROM bridge_area_h3_weight bw
                JOIN bridge_area_h3_weight_store bs
                    ON bs.area_id = bw.area_id AND bs.h3_index = bw.h3_index
                JOIN dim_area da ON da.area_id = bw.area_id
                GROUP BY da.area_name, bw.area_id
            )
            SELECT * FROM comparison
            ORDER BY max_diff DESC
        """)

        rows = session.execute(summary_sql).fetchall()

        print(f"\n{'상권명':20} {'H3수':>6} {'점포H3':>6} {'평균차이':>10} {'최대차이':>10}")
        print("-" * 60)
        for row in rows:
            print(f"{row.area_name[:20]:20} {row.h3_count:>6} {row.h3_with_stores:>6} "
                  f"{row.avg_diff:>10.4f} {row.max_diff:>10.4f}")


def main():
    stats = compute_store_weights()

    # 상세 비교 리포트
    if stats["h3_records"] > 0:
        compare_weights_report()

    # 실패 시 exit code 1
    if stats["h3_records"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
