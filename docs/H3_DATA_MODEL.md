# K-CIA Lite H3 데이터 모델 설명서

## 1. 개요

K-CIA Lite는 H3 hexagon 그리드 시스템을 사용하여 상권/행정동 데이터를 시각화합니다.
이 문서는 데이터가 어떻게 매핑되고 집계되는지 설명합니다.

---

## 2. 핵심 개념

### 2.1 영역 타입 (Area Types)

| 타입 | 설명 | 예시 |
|------|------|------|
| `COMMERCIAL_AREA` | 서울시 상권 영역 | 성원중학교, 뚝섬역상점가, 서울숲카페거리 |
| `ADMIN_DONG` | 행정동 경계 | 성수1가1동, 성수2가3동 |

### 2.2 H3 Hexagon

- **해상도**: res=10 (한 변 약 15m, 면적 약 0.015km²)
- **특징**: 균일한 크기의 육각형 그리드로 전체 영역을 분할
- **장점**: 위치 기반 집계에 최적화, 시각적으로 균일한 표현

---

## 3. 데이터베이스 스키마

### 3.1 차원 테이블

```sql
-- 영역 정의
dim_area (
    area_id        SERIAL PRIMARY KEY,
    area_type      VARCHAR(20),      -- 'COMMERCIAL_AREA' | 'ADMIN_DONG'
    area_code      VARCHAR(20),      -- 공공데이터 코드
    area_name      VARCHAR(100),     -- 표시명
    geom           GEOMETRY          -- 폴리곤 경계 (PostGIS)
)

-- 영역-H3 매핑 (핵심!)
bridge_area_h3_weight (
    area_id        INT,
    h3_index       VARCHAR(20),      -- H3 인덱스 (예: '8a30e1c12017fff')
    weight         DECIMAL(10,6)     -- 겹침 비율 (0.0 ~ 1.0)
)
```

### 3.2 팩트 테이블

```sql
-- 분기별 매출 (상권 단위)
fact_sales_area_qtr (
    area_id        INT,
    qtr            VARCHAR(5),       -- '20244' = 2024년 4분기
    cat_id         INT,              -- 업종
    sales_amt      DECIMAL,          -- 매출액
    sales_cnt      INT               -- 거래건수
)

-- 분기별 유동인구 (상권 단위)
fact_flow_area_qtr (
    area_id        INT,
    qtr            VARCHAR(5),
    flow_total     DECIMAL,          -- 총 유동인구
    flow_by_hour   JSONB,            -- 시간대별
    flow_by_demo   JSONB             -- 연령/성별
)
```

---

## 4. H3 Weight 매핑 원리

### 4.1 Weight란?

**Weight = H3 hexagon이 특정 영역(상권/행정동)과 겹치는 비율**

```
weight = (hexagon ∩ 영역 폴리곤) / hexagon 면적
```

### 4.2 예시

```
┌─────────────────────────────────────┐
│         성원중학교 상권             │
│                                     │
│     ⬢ A (w=1.0)    ⬢ B (w=1.0)     │
│     100% 상권 안    100% 상권 안    │
│                                     │
│     ⬢ C (w=0.43)                   │──── 상권 경계선
│     ╲                               │
└──────╲──────────────────────────────┘
        ╲
         ╲ (57%는 상권 밖 = 성수1가1동)
```

| Hexagon | 위치 | Weight | 의미 |
|---------|------|--------|------|
| A | 상권 중심부 | 1.0 | 100% 상권 내부 |
| B | 상권 중심부 | 1.0 | 100% 상권 내부 |
| C | 상권 경계부 | 0.43 | 43%만 상권 내부 |

### 4.3 하나의 Hexagon, 여러 영역

하나의 hexagon이 여러 영역과 동시에 매핑될 수 있습니다:

```sql
-- hexagon '8a30e1c1254ffff'의 매핑
h3_index          | area_name    | area_type       | weight
------------------|--------------|-----------------|-------
8a30e1c1254ffff   | 성수1가1동   | ADMIN_DONG      | 1.0
8a30e1c1254ffff   | 성원중학교   | COMMERCIAL_AREA | 0.429
```

이 hexagon은:
- 행정동 관점: 성수1가1동에 100% 포함
- 상권 관점: 성원중학교에 43% 포함 (나머지는 상권 밖)

---

## 5. API 집계 로직

### 5.1 SQL 쿼리 구조

```sql
WITH all_hex AS (
    -- 모든 영역-hexagon 매핑
    SELECT h3_index, area_id, weight, area_type, area_name
    FROM bridge_area_h3_weight bw
    JOIN dim_area da ON da.area_id = bw.area_id
),
primary_area AS (
    -- 표시용: 선택된 area_type 중 가장 높은 weight
    SELECT DISTINCT ON (h3_index) h3_index, area_id, area_name
    FROM all_hex
    WHERE area_type = :area_type  -- 'COMMERCIAL_AREA' 또는 'ADMIN_DONG'
    ORDER BY h3_index, weight DESC
)
SELECT
    hw.h3_index,
    pa.area_id,
    pa.area_name,
    -- 각 hexagon이 겹치는 모든 영역의 fact 데이터를 weight로 가중 합산
    SUM(s.sales_amt * hw.weight) AS sales_amt,
    SUM(f.flow_total * hw.weight) AS flow_total
FROM all_hex hw
LEFT JOIN primary_area pa ON pa.h3_index = hw.h3_index
LEFT JOIN fact_sales_area_qtr s ON s.area_id = hw.area_id
LEFT JOIN fact_flow_area_qtr f ON f.area_id = hw.area_id
GROUP BY hw.h3_index, pa.area_id, pa.area_name
```

### 5.2 집계 결과 해석

| h3_index | area_name | weight | 상권 매출 | 최종 표시 매출 |
|----------|-----------|--------|-----------|----------------|
| A | 성원중학교 | 1.0 | 143억 | 143억 × 1.0 = **143억** |
| B | 성원중학교 | 1.0 | 143억 | 143억 × 1.0 = **143억** |
| C | 성원중학교 | 0.43 | 143억 | 143억 × 0.43 = **61억** |

**핵심**: 동일 상권이라도 hexagon의 weight(겹침 비율)에 따라 표시되는 값이 다릅니다.

---

## 6. 시각화 의미

### 6.1 3D 맵에서의 해석

```
높이 = 유동인구 또는 매출
색상 = 매출 규모 (녹색 → 노랑 → 빨강)

        ▲ 높이
        │
    ████████  상권 중심부 (w=1.0)
    ████████  높은 값
    ████████
        │
    ████      상권 경계부 (w=0.43)
    ████      낮은 값
        │
    ░░░░      상권 밖 (회색)
    ░░░░      데이터 없음
```

### 6.2 사용자 관점

| 시각적 표현 | 의미 |
|-------------|------|
| 높고 붉은 hexagon | 상권 핵심부, 매출 집중 |
| 낮고 녹색 hexagon | 상권 가장자리 또는 저매출 |
| 회색 hexagon | 상권 영역 밖 (주거지 등) |

---

## 7. 동일 상권 내 값 차이 FAQ

### Q: 같은 "성원중학교" 상권인데 왜 매출이 다른가요?

**A**: 공공데이터는 **상권 전체** 단위로 제공됩니다. 
K-CIA는 이를 H3 hexagon으로 분할하여 표시할 때, 
각 hexagon이 상권과 겹치는 비율(weight)을 반영합니다.

- 상권 중심부 hexagon: weight=1.0 → 매출 100% 표시
- 상권 경계부 hexagon: weight=0.43 → 매출 43% 표시

### Q: 실제 매출이 그 위치에서 발생한 건가요?

**A**: 아닙니다. 공공데이터는 상권 전체의 집계 데이터입니다.
hexagon별 값은 **시각화를 위한 비례 배분**이며,
실제 해당 위치의 매출을 의미하지 않습니다.

### Q: 정확한 상권 매출을 보려면?

**A**: 상권을 클릭하면 사이드바에 **상권 전체 합계**가 표시됩니다.
또는 `/api/map/hexagon/{h3_index}` 상세 API에서 
해당 hexagon이 속한 영역들의 정보를 확인할 수 있습니다.

---

## 8. 데이터 흐름 다이어그램

```
[공공데이터]                    [K-CIA DB]                      [API/UI]
     │                              │                              │
     │  상권별 매출/유동인구        │                              │
     │  (예: 성원중학교 143억)      │                              │
     ▼                              │                              │
┌─────────────┐                     │                              │
│ fact_sales  │──────────────────▶ dim_area ◀──────────────────────│
│ area_qtr    │                   (상권 정의)                      │
└─────────────┘                     │                              │
                                    ▼                              │
                            bridge_area_h3_weight                  │
                           (상권→H3 매핑+weight)                   │
                                    │                              │
                                    ▼                              │
                            ┌─────────────────┐                    │
                            │  API 집계 쿼리  │                    │
                            │  (weight 가중)  │                    │
                            └────────┬────────┘                    │
                                     │                              │
                                     ▼                              │
                            ┌─────────────────┐     ┌──────────────┐
                            │ HexagonSummary  │────▶│  3D HexMap   │
                            │ (h3별 집계값)   │     │  (Deck.gl)   │
                            └─────────────────┘     └──────────────┘
```

---

## 9. 기술 참고

### 9.1 H3 해상도별 크기

| Resolution | 평균 면적 | 변 길이 | 용도 |
|------------|-----------|---------|------|
| 8 | 0.74 km² | 461m | 광역 분석 |
| 9 | 0.11 km² | 174m | 상권 분석 (기본) |
| **10** | **0.015 km²** | **66m** | **상세 분석 (현재 사용)** |
| 11 | 0.002 km² | 25m | 초정밀 분석 |

### 9.2 Weight 계산 (ETL)

```python
# etl/processors/h3_mapper.py
from h3 import polyfill, h3_to_geo_boundary
from shapely.geometry import Polygon
from shapely.ops import intersection

def calculate_weight(h3_index: str, area_polygon: Polygon) -> float:
    """H3 hexagon과 영역 폴리곤의 겹침 비율 계산"""
    hex_boundary = h3_to_geo_boundary(h3_index, geo_json=True)
    hex_polygon = Polygon(hex_boundary)
    
    intersect = intersection(hex_polygon, area_polygon)
    weight = intersect.area / hex_polygon.area
    
    return round(weight, 6)
```

### 9.3 관련 파일

| 파일 | 역할 |
|------|------|
| `etl/processors/h3_mapper.py` | H3 매핑 및 weight 계산 |
| `backend/api/map.py` | hexagon 집계 API |
| `backend/api/schemas.py` | API 응답 스키마 |
| `frontend/src/components/map/HexMap.tsx` | 3D 시각화 |

---

## 10. 버전 이력

| 버전 | 날짜 | 변경사항 |
|------|------|----------|
| 1.0 | 2026-02-02 | 초기 문서 작성 |
