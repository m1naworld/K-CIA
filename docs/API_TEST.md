# K-CIA Lite — API 테스트 가이드

## 사전 준비

```bash
# DB + Backend 기동
docker compose up -d db backend

# 기동 확인
curl http://localhost:8000/health
# → {"status":"ok"}
```

## 엔드포인트 테스트

### 1. 헬스체크

```bash
curl http://localhost:8000/health
```

### 2. 업종 목록

```bash
curl http://localhost:8000/api/data/categories
```

응답: `{ "data": [{ "cat_id", "service_code", "service_name" }, ...], "total": 100 }`

### 3. 영역 프리셋 (전체)

```bash
curl http://localhost:8000/api/data/area-scope
```

응답: 행정동 4개 + 상권 23개 = 27건

### 4. 영역 프리셋 (행정동만)

```bash
curl "http://localhost:8000/api/data/area-scope?area_type=ADMIN_DONG"
```

응답: 4건 (성수1가1동, 1가2동, 2가1동, 2가3동)

### 5. 영역 프리셋 (상권만)

```bash
curl "http://localhost:8000/api/data/area-scope?area_type=COMMERCIAL_AREA"
```

응답: 23건

### 6. H3 헥사곤 그리드

```bash
# 상권 기준 (기본)
curl "http://localhost:8000/api/map/hexagons?area_type=COMMERCIAL_AREA"

# 행정동 기준
curl "http://localhost:8000/api/map/hexagons?area_type=ADMIN_DONG"

# 업종 필터 (예: 커피-Loss/음료)
curl "http://localhost:8000/api/map/hexagons?area_type=COMMERCIAL_AREA&category=CS100008"

# 분기 지정
curl "http://localhost:8000/api/map/hexagons?area_type=COMMERCIAL_AREA&qtr=20244"
```

응답: `{ "data": [{ "h3_index", "lat", "lng", "sales_amt", ... }], "data_asof", "area_type", "filters" }`

### 7. 특정 헥사곤 상세

> h3_index는 6번 결과에서 복사하여 사용

```bash
# 예시 (실제 h3_index로 교체 필요)
curl "http://localhost:8000/api/map/hexagon/8930e1c1353ffff"
```

응답: flow/sales/competition/growth/risk 카드 + data_asof

## JSON 보기 좋게 출력

모든 curl 명령 끝에 파이프 추가:

```bash
curl http://localhost:8000/api/data/categories | python3 -m json.tool
```

## 주의사항

- URL에 `?` 파라미터가 있으면 반드시 **따옴표**로 감싸야 합니다
- 분기 포맷: `20244` (= 2024년 4분기), `Q` 없음
- h3_index는 6번 hexagons 응답에서 실제 값을 복사하여 사용
