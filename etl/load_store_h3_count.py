"""H3별 점포 수 집계 ETL.

raw_semas_store 테이블에서 H3 인덱스별 점포 수를 집계하여
fact_store_h3_count 테이블에 적재.

Usage:
    python -m etl.load_store_h3_count
"""

from __future__ import annotations

import sys
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from etl.config import DATABASE_URL


def load_store_h3_count() -> dict[str, int]:
    """H3별 점포 수 집계 및 적재.

    Returns:
        집계 통계 딕셔너리
    """
    stats = {
        "source_stores": 0,
        "unique_h3": 0,
        "inserted": 0,
        "min_count": 0,
        "max_count": 0,
        "avg_count": 0.0,
    }

    print("=" * 60)
    print("H3별 점포 수 집계 시작")
    print("=" * 60)

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # 1. 소스 데이터 확인
        stats["source_stores"] = session.execute(
            text("SELECT COUNT(*) FROM raw_semas_store WHERE h3_index IS NOT NULL")
        ).scalar() or 0

        if stats["source_stores"] == 0:
            print("✗ raw_semas_store에 H3 데이터 없음. 먼저 load_semas_stores를 실행하세요.")
            return stats

        print(f"소스 점포 수: {stats['source_stores']:,}")

        # 2. H3별 집계 및 적재 (UPSERT)
        now = datetime.utcnow()

        upsert_sql = text("""
            INSERT INTO fact_store_h3_count (h3_index, store_cnt, updated_at)
            SELECT h3_index, COUNT(*) as store_cnt, :now
            FROM raw_semas_store
            WHERE h3_index IS NOT NULL
            GROUP BY h3_index
            ON CONFLICT (h3_index) DO UPDATE SET
                store_cnt = EXCLUDED.store_cnt,
                updated_at = EXCLUDED.updated_at
        """)

        result = session.execute(upsert_sql, {"now": now})
        session.commit()

        # 3. 집계 통계 조회
        agg_stats = session.execute(text("""
            SELECT
                COUNT(*) as unique_h3,
                MIN(store_cnt) as min_cnt,
                MAX(store_cnt) as max_cnt,
                AVG(store_cnt)::numeric(10,2) as avg_cnt
            FROM fact_store_h3_count
        """)).fetchone()

        stats["unique_h3"] = agg_stats.unique_h3 or 0
        stats["inserted"] = stats["unique_h3"]
        stats["min_count"] = agg_stats.min_cnt or 0
        stats["max_count"] = agg_stats.max_cnt or 0
        stats["avg_count"] = float(agg_stats.avg_cnt or 0)

        print(f"\nH3 집계 완료:")
        print(f"  유니크 H3 수: {stats['unique_h3']:,}")
        print(f"  점포 수 범위: {stats['min_count']} ~ {stats['max_count']}")
        print(f"  H3당 평균 점포 수: {stats['avg_count']:.2f}")

        # 4. 점포 수 분포 (Top 10)
        top_h3 = session.execute(text("""
            SELECT h3_index, store_cnt
            FROM fact_store_h3_count
            ORDER BY store_cnt DESC
            LIMIT 10
        """)).fetchall()

        print("\n점포 수 상위 H3 (Top 10):")
        for row in top_h3:
            print(f"  {row.h3_index}: {row.store_cnt}개")

        # 5. 점포 수 분포 히스토그램
        dist = session.execute(text("""
            SELECT
                CASE
                    WHEN store_cnt = 1 THEN '1'
                    WHEN store_cnt BETWEEN 2 AND 5 THEN '2-5'
                    WHEN store_cnt BETWEEN 6 AND 10 THEN '6-10'
                    WHEN store_cnt BETWEEN 11 AND 20 THEN '11-20'
                    WHEN store_cnt BETWEEN 21 AND 50 THEN '21-50'
                    ELSE '50+'
                END as bucket,
                COUNT(*) as h3_count
            FROM fact_store_h3_count
            GROUP BY 1
            ORDER BY MIN(store_cnt)
        """)).fetchall()

        print("\n점포 수 분포:")
        for row in dist:
            print(f"  {row.bucket:>5} 개: {row.h3_count:,} H3")

    print("\n" + "=" * 60)
    print("H3별 점포 수 집계 완료")
    print(f"통계: {stats}")
    print("=" * 60)

    return stats


def main():
    stats = load_store_h3_count()

    # 실패 시 exit code 1
    if stats["unique_h3"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
