"""
Golden Query Regression Tests for K-CIA SQL Agent.

Usage (Docker):
    docker compose run --rm --entrypoint bash etl -c "python tests/test_sql_agent.py"
    
Usage (Integration with API key):
    docker compose run --rm --entrypoint bash etl -c "python tests/test_sql_agent.py --integration"
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

GOLDEN_QUERIES_PATH = Path(__file__).parent / "golden_queries" / "golden_queries.json"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://kcia:kcia_local_pw@db:5432/kcia")


def load_golden_queries() -> list[dict]:
    """Load golden query definitions from JSON file."""
    with open(GOLDEN_QUERIES_PATH) as f:
        data = json.load(f)
    return data["queries"]


def get_db_engine():
    """Create SQLAlchemy engine."""
    return create_engine(DATABASE_URL)


def run_validation_tests() -> bool:
    """Run validation SQL tests."""
    engine = get_db_engine()
    golden_queries = load_golden_queries()
    
    print("=" * 60)
    print("Golden Query Validation Tests (DB Direct)")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for query in golden_queries:
        query_id = query["id"]
        query_name = query["name"]
        validation_sql = query.get("validation_sql")
        
        if not validation_sql:
            print(f"[SKIP] {query_id}: No validation SQL")
            continue
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text(validation_sql))
                rows = result.fetchall()
                columns = list(result.keys())
            
            row_count = len(rows)
            min_rows = query.get("expected_row_count_min", 1)
            max_rows = query.get("expected_row_count_max", 1000)
            
            if row_count < min_rows:
                print(f"[FAIL] {query_id}: Expected >= {min_rows} rows, got {row_count}")
                failed += 1
                continue
            
            if row_count > max_rows:
                print(f"[FAIL] {query_id}: Expected <= {max_rows} rows, got {row_count}")
                failed += 1
                continue
            
            # Check top result if specified
            check_passed = True
            if "expected_top_result" in query and rows:
                top_row = dict(zip(columns, rows[0]))
                for key, expected in query["expected_top_result"].items():
                    if key.endswith("_contains"):
                        actual_key = key.replace("_contains", "")
                        if expected not in str(top_row.get(actual_key, "")):
                            print(f"[FAIL] {query_id}: Expected '{expected}' in {actual_key}, got '{top_row.get(actual_key)}'")
                            failed += 1
                            check_passed = False
                            break
            
            if check_passed:
                # Show sample result
                if rows:
                    sample = dict(zip(columns, rows[0]))
                    sample_str = ", ".join(f"{k}={v}" for k, v in list(sample.items())[:3])
                    print(f"[PASS] {query_name}: {row_count} rows | {sample_str}...")
                else:
                    print(f"[PASS] {query_name}: {row_count} rows")
                passed += 1
            
        except Exception as e:
            print(f"[FAIL] {query_id}: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Validation Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


def run_integration_tests() -> bool:
    """Run integration tests via HTTP API (requires backend running)."""
    import urllib.request
    import urllib.error
    
    api_url = os.getenv("API_URL", "http://backend:8000")
    
    golden_queries = load_golden_queries()
    
    print("=" * 60)
    print("SQL Agent Integration Tests (via API)")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for query in golden_queries:
        query_id = query["id"]
        query_name = query["name"]
        question = query["question"]
        expected_route = query.get("expected_route", "sql")
        expected_patterns = query.get("expected_sql_patterns", [])
        
        try:
            # Make HTTP request to chat API
            req_data = json.dumps({"question": question}).encode("utf-8")
            req = urllib.request.Request(
                f"{api_url}/api/chat",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=60) as resp:
                response_text = resp.read().decode("utf-8")
            
            # Parse SSE events
            events = {}
            current_event = None
            for line in response_text.split("\n"):
                if line.startswith("event: "):
                    current_event = line[7:]
                elif line.startswith("data: ") and current_event:
                    events[current_event] = json.loads(line[6:])
            
            # Check route
            actual_route = events.get("routing", {}).get("route", "unknown")
            route_ok = actual_route in (expected_route, "both") if expected_route != "both" else actual_route == "both"
            
            # Check SQL
            sql_event = events.get("sql", {})
            sql_text = sql_event.get("sql", "")
            row_count = sql_event.get("row_count", 0)
            
            # Check patterns (all must match)
            patterns_found = []
            patterns_missing = []
            for pattern in expected_patterns:
                if pattern.lower() in sql_text.lower():
                    patterns_found.append(pattern)
                else:
                    patterns_missing.append(pattern)
            
            # Check patterns_any (at least one must match)
            patterns_any = query.get("expected_sql_patterns_any", [])
            any_matched = not patterns_any or any(p.lower() in sql_text.lower() for p in patterns_any)
            
            # Check insight if expected
            insight_ok = True
            if query.get("has_insight"):
                insight = events.get("insight", {})
                required_fields = query.get("insight_required_fields", [])
                for field in required_fields:
                    if field not in insight:
                        insight_ok = False
                        break
            
            # Determine pass/fail
            if not route_ok:
                print(f"[FAIL] {query_name}: Wrong route - expected '{expected_route}', got '{actual_route}'")
                failed += 1
            elif not sql_text and expected_route in ("sql", "both"):
                print(f"[FAIL] {query_name}: No SQL generated")
                failed += 1
            elif patterns_missing:
                print(f"[FAIL] {query_name}: Missing patterns - {patterns_missing}")
                print(f"       SQL: {sql_text[:150]}...")
                failed += 1
            elif not any_matched:
                print(f"[FAIL] {query_name}: None of patterns_any matched - {patterns_any}")
                failed += 1
            elif not insight_ok:
                print(f"[FAIL] {query_name}: Missing insight fields")
                failed += 1
            else:
                print(f"[PASS] {query_name}: route={actual_route}, rows={row_count}, patterns={len(patterns_found)}/{len(expected_patterns)}")
                passed += 1
                
        except urllib.error.URLError as e:
            print(f"[SKIP] {query_name}: API not available - {e}")
        except Exception as e:
            print(f"[FAIL] {query_id}: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Integration Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


def main():
    """Main entry point."""
    args = sys.argv[1:]
    
    # Run validation tests (always)
    validation_ok = run_validation_tests()
    
    # Run integration tests if requested
    integration_ok = True
    if "--integration" in args or "-i" in args:
        print()
        integration_ok = run_integration_tests()
    
    # Exit code
    success = validation_ok and integration_ok
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
