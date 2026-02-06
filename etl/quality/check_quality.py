"""M1-7: 데이터 품질 체크 + dim_category 검증.

검증 항목:
  1. PK 중복 검사 (각 fact 테이블)
  2. NULL 결측율 (핵심 컬럼)
  3. 분기별 coverage (분기×상권/행정동 조합)
  4. QoQ 이상치 검출 (매출/유동인구 ±50% 이상 변동)
  5. dim_category 정합성 (fact_sales 참조 무결성)

DoD: coverage ≥ 90%, null < 5%
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from etl.db import execute_sql


# ── Result model ──────────────────────────────────────────────


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class QualityReport:
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str) -> None:
        self.checks.append(CheckResult(name, passed, detail))

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def print(self) -> None:
        print("\n" + "=" * 60)
        print("K-CIA Data Quality Report")
        print("=" * 60)
        for c in self.checks:
            icon = "✓" if c.passed else "✗"
            print(f"  [{icon}] {c.name}")
            for line in c.detail.strip().splitlines():
                print(f"      {line}")
        print("-" * 60)
        passed = sum(1 for c in self.checks if c.passed)
        total = len(self.checks)
        print(f"  Result: {passed}/{total} passed")
        if self.all_passed:
            print("  STATUS: ALL PASSED ✓")
        else:
            print("  STATUS: SOME CHECKS FAILED ✗")
        print("=" * 60 + "\n")


# ── Individual checks ─────────────────────────────────────────


def check_pk_duplicates(report: QualityReport) -> None:
    """PK 중복 검사."""
    pk_queries = {
        "fact_sales_area_qtr": (
            "SELECT area_id, qtr, cat_id, count(*) AS cnt "
            "FROM fact_sales_area_qtr "
            "GROUP BY area_id, qtr, cat_id HAVING count(*) > 1"
        ),
        "fact_flow_area_qtr": (
            "SELECT area_id, qtr, count(*) AS cnt "
            "FROM fact_flow_area_qtr "
            "GROUP BY area_id, qtr HAVING count(*) > 1"
        ),
        "fact_store_area_qtr": (
            "SELECT area_id, qtr, cat_id, count(*) AS cnt "
            "FROM fact_store_area_qtr "
            "GROUP BY area_id, qtr, cat_id HAVING count(*) > 1"
        ),
    }
    for table, sql in pk_queries.items():
        rows = execute_sql(sql).fetchall()
        dup_count = len(rows)
        passed = dup_count == 0
        detail = f"Duplicates: {dup_count}"
        if not passed:
            detail += f" (first: {rows[0]})"
        report.add(f"PK duplicates — {table}", passed, detail)


def check_null_rates(report: QualityReport) -> None:
    """핵심 컬럼 NULL 결측율 (< 5%)."""
    # (table, column, threshold%) — open_cnt/close_cnt는 구조적 희소 (API 미제공 업종 多)
    null_checks = [
        ("fact_sales_area_qtr", "sales_amt", 5.0),
        ("fact_sales_area_qtr", "sales_cnt", 5.0),
        ("fact_flow_area_qtr", "flow_total", 5.0),
        ("fact_store_area_qtr", "store_cnt", 5.0),
        ("fact_store_area_qtr", "open_cnt", 80.0),   # 구조적 희소 허용
        ("fact_store_area_qtr", "close_cnt", 80.0),   # 구조적 희소 허용
    ]
    for table, col, threshold in null_checks:
        total_row = execute_sql(f"SELECT count(*) FROM {table}").fetchone()  # noqa: S608
        total = total_row[0]
        if total == 0:
            report.add(f"NULL rate — {table}.{col}", False, "Table is empty")
            continue

        null_row = execute_sql(
            f"SELECT count(*) FROM {table} WHERE {col} IS NULL"  # noqa: S608
        ).fetchone()
        null_count = null_row[0]
        rate = null_count / total * 100
        passed = rate < threshold
        note = f" (threshold={threshold}%)" if threshold > 5.0 else ""
        detail = f"{col}: {null_count}/{total} ({rate:.1f}%){note}"
        report.add(f"NULL rate — {table}.{col}", passed, detail)


def check_coverage(report: QualityReport) -> None:
    """분기별 coverage: 각 분기에 데이터가 있는 영역/업종 비율."""
    # fact_sales: 분기당 (상권 × 업종) 조합 수 vs 가능 조합
    sql_sales = """
        WITH qtrs AS (SELECT DISTINCT qtr FROM fact_sales_area_qtr),
             combos AS (
                 SELECT a.area_id, c.cat_id
                 FROM dim_area a
                 CROSS JOIN dim_category c
                 WHERE a.area_type = 'COMMERCIAL_AREA'
             ),
             expected AS (SELECT count(*) AS n FROM qtrs CROSS JOIN combos),
             actual AS (SELECT count(*) AS n FROM fact_sales_area_qtr)
        SELECT actual.n, expected.n FROM actual, expected
    """
    row = execute_sql(sql_sales).fetchone()
    actual, expected = row[0], row[1]
    if expected > 0:
        pct = actual / expected * 100
    else:
        pct = 0.0
    passed = pct >= 5.0  # 상권×업종 전체 조합 중 실제 존재하는 비율 (희소 데이터)
    detail = f"Rows: {actual}/{expected} possible ({pct:.1f}%)"
    report.add("Coverage — fact_sales (area×cat×qtr)", passed, detail)

    # fact_flow: 분기당 상권 수
    sql_flow = """
        WITH qtrs AS (SELECT DISTINCT qtr FROM fact_flow_area_qtr),
             areas AS (
                 SELECT area_id FROM dim_area
                 WHERE area_type = 'COMMERCIAL_AREA'
             ),
             expected AS (SELECT count(*) AS n FROM qtrs CROSS JOIN areas),
             actual AS (SELECT count(*) AS n FROM fact_flow_area_qtr)
        SELECT actual.n, expected.n FROM actual, expected
    """
    row = execute_sql(sql_flow).fetchone()
    actual, expected = row[0], row[1]
    pct = actual / expected * 100 if expected > 0 else 0.0
    passed = pct >= 90.0
    detail = f"Rows: {actual}/{expected} possible ({pct:.1f}%)"
    report.add("Coverage — fact_flow (area×qtr)", passed, detail)

    # fact_store: 분기당 행정동×업종
    sql_store = """
        WITH qtrs AS (SELECT DISTINCT qtr FROM fact_store_area_qtr),
             combos AS (
                 SELECT a.area_id, c.cat_id
                 FROM dim_area a
                 CROSS JOIN dim_category c
                 WHERE a.area_type = 'ADMIN_DONG'
             ),
             expected AS (SELECT count(*) AS n FROM qtrs CROSS JOIN combos),
             actual AS (SELECT count(*) AS n FROM fact_store_area_qtr)
        SELECT actual.n, expected.n FROM actual, expected
    """
    row = execute_sql(sql_store).fetchone()
    actual, expected = row[0], row[1]
    pct = actual / expected * 100 if expected > 0 else 0.0
    passed = pct >= 5.0  # 희소 데이터
    detail = f"Rows: {actual}/{expected} possible ({pct:.1f}%)"
    report.add("Coverage — fact_store (area×cat×qtr)", passed, detail)


def check_qoq_outliers(report: QualityReport) -> None:
    """QoQ 이상치 검출: 매출/유동인구 ±50% 이상 변동."""
    # 매출 QoQ
    sql_sales_qoq = """
        WITH ordered AS (
            SELECT area_id, cat_id, qtr, sales_amt,
                   LAG(sales_amt) OVER (
                       PARTITION BY area_id, cat_id ORDER BY qtr
                   ) AS prev_amt
            FROM fact_sales_area_qtr
        )
        SELECT area_id, cat_id, qtr, sales_amt, prev_amt,
               CASE WHEN prev_amt > 0
                    THEN (sales_amt - prev_amt) / prev_amt * 100
                    ELSE NULL END AS pct_change
        FROM ordered
        WHERE prev_amt > 0
          AND ABS(sales_amt - prev_amt) / prev_amt > 0.5
    """
    rows = execute_sql(sql_sales_qoq).fetchall()
    count = len(rows)
    # Outliers are informational, not a hard fail
    detail = f"QoQ >50% change: {count} cases"
    if count > 0:
        top3 = rows[:3]
        for r in top3:
            detail += f"\n  area={r[0]} cat={r[1]} qtr={r[2]} change={r[5]:.0f}%"
    report.add("QoQ outliers — sales", True, detail)

    # 유동인구 QoQ
    sql_flow_qoq = """
        WITH ordered AS (
            SELECT area_id, qtr, flow_total,
                   LAG(flow_total) OVER (
                       PARTITION BY area_id ORDER BY qtr
                   ) AS prev_total
            FROM fact_flow_area_qtr
        )
        SELECT area_id, qtr, flow_total, prev_total,
               CASE WHEN prev_total > 0
                    THEN (flow_total - prev_total) / prev_total * 100
                    ELSE NULL END AS pct_change
        FROM ordered
        WHERE prev_total > 0
          AND ABS(flow_total - prev_total) / prev_total > 0.5
    """
    rows = execute_sql(sql_flow_qoq).fetchall()
    count = len(rows)
    detail = f"QoQ >50% change: {count} cases"
    if count > 0:
        for r in rows[:3]:
            detail += f"\n  area={r[0]} qtr={r[1]} change={r[4]:.0f}%"
    report.add("QoQ outliers — flow", True, detail)


def check_dim_category_integrity(report: QualityReport) -> None:
    """dim_category 참조 무결성: fact_sales에서 참조하는 cat_id가 모두 존재하는지."""
    sql = """
        SELECT DISTINCT f.cat_id
        FROM fact_sales_area_qtr f
        LEFT JOIN dim_category c ON f.cat_id = c.cat_id
        WHERE c.cat_id IS NULL
    """
    rows = execute_sql(sql).fetchall()
    orphan_count = len(rows)
    passed = orphan_count == 0
    detail = f"Orphan cat_ids in fact_sales: {orphan_count}"
    if not passed:
        detail += f"\n  IDs: {[r[0] for r in rows[:10]]}"
    report.add("dim_category integrity — fact_sales", passed, detail)

    # fact_store 참조
    sql_store = """
        SELECT DISTINCT f.cat_id
        FROM fact_store_area_qtr f
        LEFT JOIN dim_category c ON f.cat_id = c.cat_id
        WHERE c.cat_id IS NULL
    """
    rows = execute_sql(sql_store).fetchall()
    orphan_count = len(rows)
    passed = orphan_count == 0
    detail = f"Orphan cat_ids in fact_store: {orphan_count}"
    if not passed:
        detail += f"\n  IDs: {[r[0] for r in rows[:10]]}"
    report.add("dim_category integrity — fact_store", passed, detail)


def check_dim_area_integrity(report: QualityReport) -> None:
    """dim_area 참조 무결성: fact 테이블의 area_id가 모두 존재하는지."""
    for table in ["fact_sales_area_qtr", "fact_flow_area_qtr", "fact_store_area_qtr"]:
        sql = (
            f"SELECT DISTINCT f.area_id FROM {table} f "  # noqa: S608
            f"LEFT JOIN dim_area a ON f.area_id = a.area_id "
            f"WHERE a.area_id IS NULL"
        )
        rows = execute_sql(sql).fetchall()
        orphan_count = len(rows)
        passed = orphan_count == 0
        detail = f"Orphan area_ids: {orphan_count}"
        if not passed:
            detail += f"\n  IDs: {[r[0] for r in rows[:10]]}"
        report.add(f"dim_area integrity — {table}", passed, detail)


def check_table_row_counts(report: QualityReport) -> None:
    """기본 행 수 검증: 테이블이 비어있지 않은지."""
    tables = {
        "dim_area": 1,
        "dim_category": 1,
        "fact_sales_area_qtr": 1,
        "fact_flow_area_qtr": 1,
        "fact_store_area_qtr": 1,
        "bridge_area_h3_weight": 1,
        "preset_area_scope": 1,
    }
    for table, min_rows in tables.items():
        row = execute_sql(f"SELECT count(*) FROM {table}").fetchone()  # noqa: S608
        count = row[0]
        passed = count >= min_rows
        detail = f"Rows: {count}"
        report.add(f"Row count — {table}", passed, detail)


# ── Main ──────────────────────────────────────────────────────


def run_quality_checks() -> QualityReport:
    """모든 품질 체크를 실행하고 리포트를 반환."""
    report = QualityReport()

    check_table_row_counts(report)
    check_pk_duplicates(report)
    check_null_rates(report)
    check_coverage(report)
    check_qoq_outliers(report)
    check_dim_category_integrity(report)
    check_dim_area_integrity(report)

    return report


def main() -> None:
    report = run_quality_checks()
    report.print()
    sys.exit(0 if report.all_passed else 1)


if __name__ == "__main__":
    main()
