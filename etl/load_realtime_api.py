"""Load D11 (실시간 도시데이터) via Seoul Open API → fact_realtime_congestion_area.

Usage:
    docker compose run --rm --entrypoint python etl -m etl.load_realtime_api
    docker compose run --rm --entrypoint python etl -m etl.load_realtime_api 성수역
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any

from etl.collectors.seoul_api_collector import SeoulAPICollector
from etl.db import execute_sql

# D11 API 장소명 → 기존 COMMERCIAL_AREA area_name 매핑
PLACE_TO_COMMERCIAL: dict[str, str] = {
    "성수카페거리": "성수동카페거리",
    "뚝섬역": "뚝섬역",
}


def resolve_area_id(place_name: str) -> int | None:
    """Resolve D11 place name to existing COMMERCIAL_AREA area_id."""
    commercial_name = PLACE_TO_COMMERCIAL.get(place_name, place_name)
    result = execute_sql(
        """
        SELECT area_id FROM dim_area
        WHERE area_type = 'COMMERCIAL_AREA' AND area_name = :name
        """,
        {"name": commercial_name},
    )
    rows = list(result)
    if rows:
        return rows[0][0]

    # fallback: LIKE 검색
    result = execute_sql(
        """
        SELECT area_id, area_name FROM dim_area
        WHERE area_type = 'COMMERCIAL_AREA' AND area_name LIKE :pattern
        LIMIT 1
        """,
        {"pattern": f"%{place_name}%"},
    )
    rows = list(result)
    if rows:
        print(f"  [INFO] Fuzzy matched '{place_name}' → '{rows[0][1]}' (area_id={rows[0][0]})")
        return rows[0][0]

    print(f"  [WARN] No COMMERCIAL_AREA found for '{place_name}'")
    return None


def fetch_realtime_data(collector: SeoulAPICollector, place_name: str) -> dict[str, Any] | None:
    """Fetch realtime data for a single place."""
    try:
        url = f"http://openapi.seoul.go.kr:8088/{collector.api_key}/json/citydata/1/5/{place_name}"
        response = collector.session.get(url, timeout=30)
        data = response.json()
        
        if "CITYDATA" in data:
            return data["CITYDATA"]
        elif "citydata" in data:
            return data["citydata"]
        elif "RESULT" in data:
            code = data["RESULT"].get("CODE", "")
            msg = data["RESULT"].get("MESSAGE", "")
            print(f"  [WARN] API error for {place_name}: [{code}] {msg[:50]}")
            return None
        else:
            print(f"  [WARN] Unexpected response for {place_name}: {list(data.keys())}")
            return None
            
    except Exception as e:
        print(f"  [ERROR] Failed to fetch {place_name}: {e}")
        return None


def upsert_realtime_congestion(area_id: int, data: dict[str, Any]) -> bool:
    """Upsert realtime congestion data."""
    ts = datetime.now(timezone.utc)
    
    live_ppltn = data.get("LIVE_PPLTN_STTS", [{}])
    if isinstance(live_ppltn, list) and live_ppltn:
        ppltn_data = live_ppltn[0]
    else:
        ppltn_data = {}
    
    congestion_level = ppltn_data.get("AREA_CONGEST_LVL", data.get("AREA_CONGEST_LVL"))
    ppltn_min = ppltn_data.get("AREA_PPLTN_MIN", data.get("AREA_PPLTN_MIN"))
    ppltn_max = ppltn_data.get("AREA_PPLTN_MAX", data.get("AREA_PPLTN_MAX"))
    
    execute_sql(
        """
        INSERT INTO fact_realtime_congestion_area (area_id, ts, congestion_level, ppltn_min, ppltn_max)
        VALUES (:area_id, :ts, :congestion_level, :ppltn_min, :ppltn_max)
        ON CONFLICT (area_id, ts) DO UPDATE SET
            congestion_level = EXCLUDED.congestion_level,
            ppltn_min = EXCLUDED.ppltn_min,
            ppltn_max = EXCLUDED.ppltn_max
        """,
        {
            "area_id": area_id,
            "ts": ts,
            "congestion_level": str(congestion_level) if congestion_level else None,
            "ppltn_min": int(ppltn_min) if ppltn_min else None,
            "ppltn_max": int(ppltn_max) if ppltn_max else None,
        },
    )
    return True


def main() -> None:
    print("=" * 60)
    print("Load D11 (실시간) via API → fact_realtime_congestion_area")
    print("=" * 60)
    
    places = list(PLACE_TO_COMMERCIAL.keys())
    if len(sys.argv) > 1:
        places = sys.argv[1:]
        print(f"[INFO] Using custom places: {places}")
    
    collector = SeoulAPICollector()
    
    total_upserted = 0
    
    for place in places:
        print(f"\n[Step] Fetching realtime data for {place}...")
        
        data = fetch_realtime_data(collector, place)
        if not data:
            continue
        
        area_id = resolve_area_id(place)
        if area_id is None:
            print(f"  [ERROR] No matching COMMERCIAL_AREA for {place}")
            continue
        
        if upsert_realtime_congestion(area_id, data):
            total_upserted += 1
            print(f"  Upserted: area_id={area_id}")
    
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)
    
    result = execute_sql("SELECT count(*) FROM fact_realtime_congestion_area")
    count = list(result)[0][0]
    print(f"  fact_realtime_congestion_area: {count:,} rows")
    
    result = execute_sql(
        """
        SELECT da.area_name, frc.congestion_level, frc.ppltn_min, frc.ppltn_max, frc.ts
        FROM fact_realtime_congestion_area frc
        JOIN dim_area da ON frc.area_id = da.area_id
        ORDER BY frc.ts DESC
        LIMIT 5
        """
    )
    print("\n  Recent records:")
    for row in result:
        print(f"    {row[0]}: {row[1]} ({row[2]}-{row[3]}) @ {row[4]}")
    
    if total_upserted > 0:
        print(f"\n✓ Done! Total upserted: {total_upserted}")
    else:
        print("\n✗ Warning: No data loaded")


if __name__ == "__main__":
    main()
