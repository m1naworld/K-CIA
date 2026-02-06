# K-CIA Lite — DB 조회 가이드

## 접속 방법

```bash
# Docker DB 컨테이너 실행 (꺼져있을 때)
docker compose up -d db

# psql 접속
docker exec -it k-cia-db-1 psql -U kcia -d kcia
```

접속 정보 (GUI 툴 사용 시):
```
Host:     localhost
Port:     5432
Database: kcia
User:     kcia
Password: kcia_local_pw
```

---

## psql 기본 명령어

```sql
\dt public.*          -- 테이블 목록
\d dim_area           -- 테이블 구조 확인
\x                    -- 세로 출력 토글 (넓은 테이블에 유용)
\q                    -- 나가기
```

---

## 주요 테이블

| 테이블 | 용도 | 현재 행 수 |
|--------|------|-----------|
| `dim_area` | 행정동(4) + 상권(23) 공간 기준 | 27 |
| `dim_category` | 업종 코드 | - |
| `preset_area_scope` | 성수동 프리셋 (dim_area 참조) | 27 |
| `bridge_area_h3_weight` | 폴리곤→H3 매핑 | - |
| `fact_sales_area_qtr` | 분기별 매출 | - |
| `fact_flow_area_qtr` | 분기별 유동인구 | - |
| `fact_store_area_qtr` | 분기별 점포 | - |
| `fact_realtime_congestion_area` | 실시간 혼잡도 | - |

---

## 자주 쓰는 쿼리

### 행정동 목록

```sql
SELECT area_id, area_code, area_name
FROM dim_area
WHERE area_type = 'ADMIN_DONG'
ORDER BY area_id;
```

### 상권 목록

```sql
SELECT area_id, area_code, area_name
FROM dim_area
WHERE area_type = 'COMMERCIAL_AREA'
ORDER BY area_id;
```

### 상권별 대표 행정동 (교차면적 기준)

```sql
SELECT DISTINCT ON (c.area_name)
    c.area_name  AS 상권명,
    d.area_name  AS 대표_행정동,
    round(ST_Area(ST_Intersection(c.geom, d.geom)::geography)::numeric, 0) AS 교차면적_m2
FROM dim_area c
JOIN dim_area d ON d.area_type = 'ADMIN_DONG' AND ST_Intersects(c.geom, d.geom)
WHERE c.area_type = 'COMMERCIAL_AREA'
ORDER BY c.area_name, 교차면적_m2 DESC;
```

### 면적 순 정렬

```sql
SELECT area_name, area_type,
       round(ST_Area(geom::geography)::numeric, 0) AS area_m2
FROM dim_area
ORDER BY area_type, area_m2 DESC;
```

### geometry 유효성 + SRID 확인

```sql
SELECT area_type,
       count(*),
       sum(ST_IsValid(geom)::int) AS valid,
       min(ST_SRID(geom))         AS srid
FROM dim_area
GROUP BY area_type;
```

### preset_area_scope 확인

```sql
SELECT da.area_type, count(*)
FROM preset_area_scope ps
JOIN dim_area da ON ps.area_id = da.area_id
GROUP BY da.area_type;
```

---

## 참고

- 모든 geometry는 **EPSG:4326** (WGS84, 경위도)
- `area_type`은 `'ADMIN_DONG'` 또는 `'COMMERCIAL_AREA'`
- GUI 추천: DBeaver (무료, 지도 미리보기), Postico (macOS), TablePlus (macOS)
