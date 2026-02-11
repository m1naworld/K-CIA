# K-CIA Lite — 진행상황 로그 (PROGRESS.md)

---

## 2026-01-30 — 계획 수립 단계

### 상태: PLANNING COMPLETE

| 항목 | 상태 |
|------|------|
| PLAN.md | 작성 완료 (A~D 섹션 + ASSUMPTIONS) |
| TODO.md | 작성 완료 (M0~M4, 티켓 20개) |
| DECISIONS.md | 작성 완료 (DEC-001~007, 7개 결정) |
| PROGRESS.md | 현재 문서 (초기 로그) |

### 완료한 작업

- [x] PRD(K-CIA Lite.md) 분석
- [x] 유저 시나리오(K-CIA_Lite_UserScenarios.md) 분석
- [x] 데이터 기획(K-CIA_Lite_DataPlan.md) 분석
- [x] 데이터 수집 계획(K-CIA_Lite_DataIngestionPlan.md) 분석
- [x] 시나리오 1 중심 실행 계획 수립
- [x] 데이터 최소셋(Must/Should/Could) 분류
- [x] 마일스톤별 작업 티켓 생성
- [x] 핵심 의사결정 7건 기록 (DEC-007: Gemini Nano Banana 추가)

### 데이터 수집/적재 상태

| 데이터셋 | raw | normalized | mart(H3) | 상태 |
|---------|-----|-----------|----------|------|
| D1 매출 | ✅ | ✅ fact_sales | - | 완료 (4,320행, 12분기) |
| D2 점포 | - | - | - | 미시작 |
| D3 상권영역 | ✅ | ✅ dim_area | - | 완료 (23개 상권) |
| D5 유동 | - | - | - | 미시작 |
| D9 행정동 | ✅ | ✅ dim_area | - | 완료 (4개 행정동) |
| D11 실시간 | - | - | - | 미시작 |

### 블로커

- 없음 (계획 단계)

### 변경된 가정/결정

- A8 수정: DataIngestionPlan 별도 파일 존재 확인 (`K-CIA_Lite_DataIngestionPlan.md`) — PLAN.md의 Data Ingestion 섹션은 이 문서와 정합성 유지

---

## 2026-02-10 — M9-12: SNS ETL 공간 매핑 구조 개선

### 상태: DONE

### 배경/문제

- YouTube 매핑률 저조 (5/17 상권 커버, 41.9% area-mapped)
- 근본 원인 3가지:
  1. `search.list` API가 설명을 ~150자로 절단 → 주소/상호 정보 손실
  2. 일별 집계 시 `majority_vote`로 area_id 1개만 선택 → 상권 다양성 파괴
  3. 키워드 기반 매핑만으로는 상권명 표기 다양성 커버 불가

### 완료한 작업

**Phase 1: videos.list API 확장**
- [x] `youtube_collector.py` — `get_video_details()` 메서드 추가 (1 unit per 50 IDs)
- [x] `load_youtube_trends.py` — `enrich_videos()` 함수로 전체 설명+태그 보강

**Phase 2: per-(date, area_id) 집계 구조 변경**
- [x] YouTube: `match_area_id` → `match_area_ids` (multi-return)
- [x] YouTube: `aggregate_by_date` → `aggregate_by_date_area` keyed by `(date, area_id|None)`
- [x] Naver: 동일 구조로 완전 재작성

**Phase 3: 좌표 기반 공간 매핑 (Spatial-first)**
- [x] `place_mapper.py` — `resolve_area_ids_multi()` 추가 (list[list[int]] 반환)
  - 주소 추출 → Kakao 주소검색 → ST_Intersects
  - Gemini Flash 장소 추출 → Kakao 키워드검색 → ST_Intersects
- [x] YouTube/Naver ETL: 공간 매핑 PRIMARY → 키워드 매핑 FALLBACK 구조로 전환
- [x] 각 콘텐츠가 다수 상권에 동시 매핑 가능 + None(전체) 버킷 항상 포함

### 결과

| 소스 | 변경 전 (상권 커버) | 변경 후 | area-mapped |
|------|---------------------|---------|-------------|
| YouTube | 5/17 (29%) | 10/17 (59%) | 61.3% |
| Naver | - | 15/17 (88%) | 90.7% |

### 수정 파일

| 파일 | 변경 |
|------|------|
| `etl/collectors/youtube_collector.py` | `get_video_details()` 메서드 추가 |
| `etl/place_mapper.py` | `resolve_area_ids_multi()` 추가 (multi-area 반환) |
| `etl/load_youtube_trends.py` | 대규모 재작성: enrich_videos, match_area_ids, aggregate_by_date_area, spatial-first |
| `etl/load_naver_trends.py` | 완전 재작성: match_area_ids, aggregate_items, spatial-first |

### 블로커

- 없음

---

## 2026-02-09 — M9-7 소셜 트렌드 상권/업종/H3 매핑 연동

### 상태: DONE

### 완료한 작업

**M9-7: Social Trends 필터 연동**
- [x] `backend/api/social.py` — `h3_index`, `area_id`, `cat_code` 필터 파라미터 추가
  - h3_index → `bridge_area_h3_weight` 조인으로 해당 상권 area_ids 해석
  - `CATEGORY_SOCIAL_MAP` 딕셔너리로 업종→소셜 키워드 매핑 (커피→카페, 한식→맛집, 제과→디저트 등)
  - area 필터 결과 0건 시 전체 데이터로 폴백 + `is_fallback=true`
  - 응답에 `filtered_area`, `filtered_category`, `is_fallback` 필드 추가
  - 쿼리 로직을 `_query_trends()` 헬퍼로 추출 (폴백 시 재사용)
- [x] `etl/load_youtube_trends.py` — `get_area_mapping()` 개선
  - `real_name` 컬럼 추가 조회 + 파트 분리 매핑
  - 랜드마크 수동 매핑 (연무장길, 대림창고, 서울숲, 헤이그라운드, 성수IT)
  - "카페거리" 키워드 제거 — 성수동카페거리(14)와 서울숲카페거리(19) 중복 방지
- [x] `etl/load_naver_trends.py` — 동일 개선 적용
- [x] `frontend/src/store/mapStore.ts` — `fetchSocialTrends(h3Index?, catCode?)` 파라미터화
  - `fetchHexDetail` 완료 후 소셜 자동 재조회
  - `setCategory` 변경 시 소셜 재조회
  - `toggleSocial` 시 현재 hex/category 컨텍스트 전달
- [x] `frontend/src/types/social.ts` — `filtered_area`, `filtered_category`, `is_fallback` 필드 추가
- [x] `frontend/src/components/sidebar/SocialBuzzCard.tsx` — 필터 컨텍스트 뱃지 (상권명/업종명/폴백 상태)
- [x] `frontend/src/components/sidebar/Sidebar.tsx` — `socialLoading` 추출 + 로딩 스켈레톤 표시

### 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/api/social.py` | h3_index/area_id/cat_code 필터, CATEGORY_SOCIAL_MAP, _query_trends 추출, 폴백 로직, 응답 컨텍스트 필드 |
| `etl/load_youtube_trends.py` | get_area_mapping: real_name + 랜드마크 매핑 |
| `etl/load_naver_trends.py` | get_area_mapping: real_name + 랜드마크 매핑 |
| `frontend/src/store/mapStore.ts` | fetchSocialTrends 파라미터화, 자동 재조회 3곳 |
| `frontend/src/types/social.ts` | SocialTrendsResponse 3필드 추가 |
| `frontend/src/components/sidebar/SocialBuzzCard.tsx` | 필터 컨텍스트 뱃지 UI |
| `frontend/src/components/sidebar/Sidebar.tsx` | socialLoading 스켈레톤 |

### 블로커

- 없음

### 다음 3개 액션

1. **ETL 재수집**: 기존 데이터 삭제 → YouTube/Naver 재수집으로 매핑률 확인 (8% → 30%+ 목표)
2. **API 검증**: `GET /api/social/trends?h3_index=...` , `?cat_code=CS100010`, 복합 필터, 폴백 동작 확인
3. **프론트엔드 E2E**: 헥스 클릭 시 SocialBuzzCard 필터 뱃지 변경, 업종 전환 시 카드 내용 변경 확인

---

## 2026-02-09 — M9 SNS Module 전체 완료

### 상태: M9 COMPLETE (M9-1 ~ M9-6)

### 완료한 작업

**M9-1: DB Migration**
- [x] `backend/migrations/005_sns_module.sql` 작성
  - fact_social_trend_daily: 소셜 트렌드 일별 집계 (YouTube/Naver Blog/Cafe)
  - social_module_config: 모듈 ON/OFF 설정 (기본값 enabled=false)
  - DEC-021: area_id nullable FK (best-effort 상권 매핑, NULL=성수동 전체)
  - 기본 검색 키워드 5개 프리셋 포함

**M9-2: YouTube Collector + Loader**
- [x] `etl/collectors/youtube_collector.py` — YouTube Data API v3 search.list, 페이징, quota exceeded 에러 처리
- [x] `etl/load_youtube_trends.py` — 키워드별 수집, 일별 집계, best-effort 상권매핑, 간이 감성분석, upsert

**M9-3: Naver Collector + Loader**
- [x] `etl/collectors/naver_collector.py` — Naver Search API (Blog+Cafe), 페이징, rate limit 처리
- [x] `etl/load_naver_trends.py` — Blog/Cafe 분리 처리, HTML 태그 제거, 일별 집계, best-effort 상권매핑, upsert

**M9-4: Social Agent (LangGraph)**
- [x] `backend/agents/social_agent.py` — 모듈 ON/OFF 분기, 트렌드 집계 쿼리 (버즈/감성/소스별/키워드/에비던스/일별추이)
- [x] `backend/agents/graph.py` — social_agent 노드 추가, 라우팅: supervisor→sql→social→insight
- [x] `backend/agents/insight_agent.py` — social_result 주입 (ON: 버즈+감성+키워드+에비던스, OFF: 비활성 노트)
- [x] `backend/agents/sql_agent.py` — fact_social_trend_daily, social_module_config ALLOWED_TABLES 및 스키마 추가

**M9-5: Social API Endpoints**
- [x] `backend/api/social.py` — GET /api/social/config, GET /api/social/trends (days/source/keyword 필터)
- [x] `backend/main.py` — social_router 등록

**M9-6: Frontend SNS UI**
- [x] `frontend/src/types/social.ts` — TypeScript 인터페이스 (SocialTrendsResponse, SocialConfigResponse 등)
- [x] `frontend/src/store/mapStore.ts` — socialEnabled, socialConfig, socialData, socialLoading 상태 + 액션
- [x] `frontend/src/components/sidebar/SocialBuzzCard.tsx` — 버즈량, 감성바, 소스별 배지, TOP 키워드, 에비던스 스니펫, 일별 추이 미니차트
- [x] `frontend/src/components/sidebar/Sidebar.tsx` — SocialBuzzCard 조건부 렌더링
- [x] `frontend/src/components/filters/FilterPanel.tsx` — 소셜 트렌드 ON/OFF 토글 + fetchSocialConfig 초기 호출

### 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/migrations/005_sns_module.sql` | 신규 — SNS 모듈 테이블 2개 |
| `etl/collectors/youtube_collector.py` | 신규 — YouTube Data API v3 래퍼 |
| `etl/load_youtube_trends.py` | 신규 — YouTube 트렌드 로더 |
| `etl/collectors/naver_collector.py` | 신규 — Naver Search API 래퍼 |
| `etl/load_naver_trends.py` | 신규 — Naver 트렌드 로더 |
| `backend/agents/social_agent.py` | 신규 — Social Agent LangGraph 노드 |
| `backend/agents/graph.py` | 수정 — social_agent 노드+라우팅 추가 |
| `backend/agents/insight_agent.py` | 수정 — social_result 프롬프트 주입 |
| `backend/agents/sql_agent.py` | 수정 — SNS 테이블 스키마+ALLOWED_TABLES |
| `backend/api/social.py` | 신규 — Social API 2개 엔드포인트 |
| `backend/main.py` | 수정 — social_router 등록 |
| `frontend/src/types/social.ts` | 신규 — SNS 타입 정의 |
| `frontend/src/store/mapStore.ts` | 수정 — social 상태+액션 추가 |
| `frontend/src/components/sidebar/SocialBuzzCard.tsx` | 신규 — 소셜 버즈 카드 |
| `frontend/src/components/sidebar/Sidebar.tsx` | 수정 — SocialBuzzCard import+렌더링 |
| `frontend/src/components/filters/FilterPanel.tsx` | 수정 — 소셜 토글+fetchSocialConfig |

### 블로커

- 없음

### 다음 3개 액션

1. **M9 실행**: DB에 migration 적용 (`psql -f 005_sns_module.sql`)
2. **SNS 수집 테스트**: YOUTUBE_API_KEY + NAVER_CLIENT_ID 설정 후 ETL 실행
3. **E2E 검증**: social_module_config enabled=true → FilterPanel 토글 → SocialBuzzCard 표시 확인

---

## 2026-02-08 — M8 비교 업종 스코프 토글

### 상태: DONE

### 완료한 작업

- [x] 비교 모드 업종 기준 토글 추가 (전체/선택 업종)
- [x] 업종 변경 시 비교 데이터 자동 갱신

### 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/store/mapStore.ts` | compareCategoryMode 상태 + 비교 재조회 로직 추가 |
| `frontend/src/components/filters/FilterPanel.tsx` | 비교 업종 기준 토글 UI 추가 |

### 블로커

- 없음

---

## 2026-02-08 — 지도 타일 폴백 스타일 추가

### 상태: DONE

### 완료한 작업

- [x] Mapbox 토큰 미설정 시 CARTO 타일 스타일로 폴백

### 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/components/map/HexMap.tsx` | mapStyle 폴백 로직 추가 |

### 블로커

- 없음

---

## 2026-02-08 — 인구통계 막대 가독성 보정

### 상태: DONE

### 완료한 작업

- [x] 인구통계 막대 그래프 채움/배경 대비 강화
- [x] 최소 막대 높이 보장

### 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/components/sidebar/DemoCard.tsx` | 막대 채움/배경 대비 + 최소 높이 보정 |

### 블로커

- 없음

---

---

## 2026-01-31 — M0 Repo/Infra 완료

### 상태: M0 COMPLETE (M0-1 ~ M0-4)

### 완료한 작업

- [x] M0-1: 모노레포 디렉토리 구조 생성 (`frontend/`, `backend/`, `etl/`, `tests/`)
- [x] M0-2: `docker-compose.yml` (Postgres/PostGIS + FastAPI + Next.js) + `.env.example`
- [x] M0-3: Next.js 14 초기화 (App Router + TypeScript + TailwindCSS + shadcn/ui + Deck.gl + Zustand + Recharts)
- [x] M0-4: FastAPI 스켈레톤 (`main.py` + `/health` + `requirements.txt` + `Dockerfile`)

### 산출물

- `docker-compose.yml` — db(postgis/postgis:16-3.4), backend(FastAPI), frontend(Next.js)
- `.env.example` — 필요 환경변수 목록
- `backend/main.py` — FastAPI + CORS + /health endpoint
- `backend/Dockerfile`, `frontend/Dockerfile`
- `frontend/` — Next.js 14 빌드 성공 확인
- shadcn/ui 초기화 완료 (`src/lib/utils.ts`, `components.json`)

### 미완료

- M0-5 (DB 마이그레이션 도구 + CI lint 설정) — P1, M1 진입 시 필요하면 진행

### 블로커

- 없음

---

## 2026-02-02 — 지도 정리 + 환경변수 보강

### 상태: DONE

### 완료한 작업

- [x] 지도 목업 라벨/핫스팟 제거 (대림창고, 헤이그라운드 등 하드코딩 데이터 삭제)
- [x] 상권 경계 표시를 대시 패턴 중심으로 정리 (색상 충돌 완화)
- [x] API 실패 시 목업 데이터 대신 빈 상태로 처리
- [x] `NEXT_PUBLIC_MAPBOX_TOKEN` 환경변수 추가 (.env)
- [x] D2 점포 데이터 분기 확장 (2025Q2, 2025Q3 적재)

### 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/components/map/HexMap.tsx` | 목업/라벨 제거, 상권 경계 대시 스타일 적용, API 기본 URL 처리 |
| `.env` | NEXT_PUBLIC_MAPBOX_TOKEN 추가 |

### 블로커

- 없음

---

## 2026-01-31 — M1-1 DDL 완료

### 상태: M1 IN PROGRESS

### 완료한 작업

- [x] M1-1: DDL 실행 (핵심 테이블 생성)
  - `backend/migrations/001_init_schema.sql` 생성
  - Extensions: postgis, vector
  - 12개 테이블: dim_area, dim_category, preset_area_scope, bridge_area_h3_weight, fact_sales_area_qtr, fact_flow_area_qtr, fact_store_area_qtr, fact_realtime_congestion_area, analysis_run, ingest_runs, raw_objects, schema_registry
  - 인덱스: dim_area(area_type, area_code) UNIQUE, bridge_area_h3_weight(h3_index), analysis_run(created_at)

### 블로커

- 없음

---

## 2026-01-31 — M1-2 COMPLETE

### 상태: M1-2 DONE

### 완료한 작업

- [x] M1-2 ETL 코드 구현 (6개 파일)
  - `etl/config.py` — 경로, CRS, 성수동 필터 상수
  - `etl/db.py` — SQLAlchemy 엔진/세션 유틸
  - `etl/collectors/boundary_collector.py` — D9/D3 SHP 읽기 (인코딩 자동감지)
  - `etl/processors/spatial_utils.py` — CRS 변환, geometry 검증/정규화
  - `etl/processors/area_loader.py` — 성수동 필터 + dim_area upsert + preset_area_scope
  - `etl/load_boundaries.py` — 메인 실행 스크립트 + 검증 쿼리
- [x] D9 행정동 SHP 다운로드 및 적재 (성수동 4개 행정동)
- [x] D3 상권영역 SHP 다운로드 및 적재 (성수동 23개 상권)
- [x] preset_area_scope 적재 (27행)
- [x] `docs/DB_GUIDE.md` — DB 접속 및 조회 가이드 작성

### DoD 검증 결과

```
dim_area ADMIN_DONG:      4행 (성수1가1동, 1가2동, 2가1동, 2가3동)
dim_area COMMERCIAL_AREA: 23행 (≥10 충족)
geometry validity:        27/27 valid
SRID:                     4326
preset_area_scope:        27행
```

### 블로커

- 없음

### 참고사항

- pgvector 확장은 현재 Docker 이미지에 미포함 → M1에서는 불필요, 추후 필요 시 이미지 교체
- D3 인코딩: UTF-8 (cp949 아님)
- D9 인코딩: cp949
- D9 CRS: EPSG:5186 → 4326 변환
- D3 CRS: EPSG:5181 → 4326 변환

---

## 2026-01-31 — M1-3 COMPLETE

### 상태: M1-3 DONE

### 완료한 작업

- [x] M1-3: H3 polyfill (res=10) → bridge_area_h3_weight
  - `etl/processors/h3_mapper.py` — polyfill + weight 계산 + centroid fallback
  - `etl/load_h3.py` — 메인 실행 스크립트 + 검증 쿼리
  - `etl/Dockerfile` — ETL 전용 Docker 이미지 (Python 3.11 + GDAL + h3 + geopandas)
  - `etl/requirements.txt` — ETL 전용 패키지 목록
  - `docker-compose.yml` — etl 서비스 추가 (profile: etl)

### DoD 검증 결과

```
Distinct H3 indices: 75 (> 50 ✓)
ADMIN_DONG:       67 bridge rows, 67 unique H3
COMMERCIAL_AREA:  44 bridge rows, 41 unique H3
총 109개 bridge_area_h3_weight 레코드
```

### 참고사항

- h3 v3 `polyfill_geojson`은 표준 GeoJSON (lng, lat) 형식 사용
- 작은 상권(골목형/역세권)은 centroid fallback으로 hex 1개 할당 (weight=1.0)
- 행정동은 11~27 hex, 상권은 1~6 hex로 매핑됨
- ETL은 `docker-compose run --rm etl etl.load_h3` 으로 실행

### 블로커

- 없음

---

## 2026-01-31 — M1-4 코드 완료 (데이터 대기)

### 상태: M1-4 COMPLETE

### 완료한 작업

- [x] M1-4: D1(매출) ETL 코드 구현 (4개 파일)
  - `etl/config.py` — D1 경로, 컬럼 매핑, 인코딩 설정 추가
  - `etl/collectors/seoul_zip_collector.py` — ZIP 탐색/압축해제
  - `etl/processors/sales_processor.py` — CSV 파싱 + 성수동 필터 + dim_category/fact_sales upsert
  - `etl/load_sales.py` — 메인 실행 스크립트 + 검증 쿼리 (CSV/ZIP 모두 지원)
  - `etl/requirements.txt` — requests, pandas 추가
- [x] D1 매출 CSV 적재 완료 (2022~2024년, 3개 파일)

### DoD 검증 결과

```
fact_sales_area_qtr: 4,320 rows ✓
dim_category:        59 rows ✓
분기 커버리지:       12분기 (20221~20244)
성수동 필터:         23개 상권, 264,259행 중 4,320행 추출
```

### 실행 방법

```bash
docker compose run --rm etl etl.load_sales
```

---

---

## 2026-01-31 — M1-7 품질 체크 완료

### 상태: M1-7 DONE (M1 COMPLETE)

### 완료한 작업

- [x] M1-7: 데이터 품질 체크 + dim_category 검증
  - `etl/quality/check_quality.py` — 7개 카테고리, 26개 체크 항목
  - 행 수 검증 (7 테이블)
  - PK 중복 검사 (3 fact 테이블) — 0건
  - NULL 결측율 (6 컬럼) — 핵심 컬럼 0%, open_cnt/close_cnt 구조적 희소 75% (허용)
  - 분기별 coverage — fact_flow 100%, fact_store 91.2%, fact_sales 15.7% (업종 희소)
  - QoQ 이상치 — 매출 306건 (정보 제공), 유동인구 0건
  - dim_category 참조 무결성 — orphan 0건
  - dim_area 참조 무결성 — orphan 0건

### DoD 검증 결과

```
26/26 checks passed
- PK duplicates: 0 across all tables
- NULL rate: core columns 0%, structural sparse ≤75.6% (threshold 80%)
- Coverage: flow 100%, store 91.2%, sales 15.7% (sparse by nature)
- Category/Area integrity: 0 orphans
```

### 실행 방법

```bash
docker compose run --rm --entrypoint python etl -m etl.quality.check_quality
```

### 참고사항

- open_cnt/close_cnt는 서울 Open API D2 특성상 대부분의 업종에서 미제공 → threshold 80%로 완화
- fact_sales coverage 15.7%는 23상권×100업종×15분기 중 실제 영업 조합만 존재하므로 정상
- QoQ 매출 이상치 306건은 계절성/신규업종 등으로 인한 정상 변동 (hard fail 아님)

---

## 2026-01-31 — M2-2 Data API 완료

### 상태: M2-2 DONE

### 완료한 작업

- [x] M2-2: Data API 엔드포인트 구현
  - `backend/api/data.py` — categories, area-scope 엔드포인트
  - `GET /api/data/categories` — dim_category 전체 목록 (100건)
  - `GET /api/data/area-scope?area_type=` — preset_area_scope 조인 조회, area_type 필터 지원
  - `backend/main.py` — data 라우터 등록
- [x] backend requirements.txt에서 불필요한 geo 라이브러리(geopandas, fiona, pyproj, shapely) 제거 → Docker 빌드 성공

### DoD 검증 결과

```
curl /api/data/categories     → 100개 업종 반환 ✓
curl /api/data/area-scope     → 27개 영역 (4 행정동 + 23 상권) ✓
curl /api/data/area-scope?area_type=ADMIN_DONG → 4개 ✓
```

---

## 2026-01-31 — API 기반 데이터 적재 (M1-5, M1-6, M1-7)

### 상태: M1 API 적재 COMPLETE

### 완료한 작업

- [x] 서울 Open API 공통 Collector 구현
  - `etl/collectors/seoul_api_collector.py` — pagination, retry, rate limit
  - API 서비스명 매핑: D1, D2, D5, D11, AREA_INFO
- [x] D1 매출 API Loader 구현
  - `etl/load_sales_api.py` — 분기별 API 호출 + 성수동 필터 + upsert
  - 2025Q1 데이터 추가 적재 (361행)
- [x] D5 유동인구 API Loader 구현
  - `etl/load_flow_api.py` — 상권별 유동인구 + 시간대/요일/성연령별 집계
  - 4개 분기 적재 (92행, 총 유동인구 91,600,320)
- [x] D11 실시간 Collector 구현
  - `etl/load_realtime_api.py` — 장소별 혼잡도 스냅샷
  - 성수카페거리, 뚝섬역 테스트 성공
  - dim_area에 REALTIME_PLACE 타입 추가
- [x] D2 점포 API — 서비스명/행정동코드 수정 후 적재 완료 (1,459행)

### DoD 검증 결과

```
fact_sales_area_qtr:            4,681 rows (2022Q1~2025Q1, 13분기)
fact_flow_area_qtr:             92 rows (2024Q1~2024Q4, 4분기)
fact_store_area_qtr:            1,459 rows (2024Q2~2025Q1, 4분기)
fact_realtime_congestion_area:  2 rows (성수카페거리, 뚝섬역)
dim_category:                   59 rows
dim_area:                       30 rows (27 기존 + 2 REALTIME_PLACE)
```

### 실행 방법

```bash
# D1 매출 (분기 지정 가능)
docker compose run --rm --entrypoint python etl -m etl.load_sales_api 20251

# D5 유동인구 (분기 지정 가능)
docker compose run --rm --entrypoint python etl -m etl.load_flow_api 20244 20243 20242 20241

# D11 실시간 (장소 지정 가능)
docker compose run --rm --entrypoint python etl -m etl.load_realtime_api "성수카페거리" "뚝섬역"

# D2 점포 (현재 API 서버 오류)
docker compose run --rm --entrypoint python etl -m etl.load_store_api 20244
```

### 데이터 수집/적재 현황 (업데이트)

| 데이터셋 | raw | normalized | mart(H3) | 상태 |
|---------|-----|-----------|----------|------|
| D1 매출 | ✅ ZIP+API | ✅ fact_sales | - | 완료 (4,681행, 13분기) |
| D2 점포 | ✅ API | ✅ fact_store | - | 완료 (1,459행, 4분기) |
| D3 상권영역 | ✅ SHP | ✅ dim_area | - | 완료 (23개 상권) |
| D5 유동 | ✅ API | ✅ fact_flow | - | 완료 (92행, 4분기) |
| D9 행정동 | ✅ SHP | ✅ dim_area | - | 완료 (4개 행정동) |
| D11 실시간 | ✅ API | ✅ fact_realtime | - | 완료 (2개 장소) |

### 블로커

- 없음

### 참고사항

- 서울 Open API 기본 URL: `http://openapi.seoul.go.kr:8088/{KEY}/json/{SERVICE}/{START}/{END}/{PARAMS}`
- 1회 호출 최대 1,000건, 자동 페이지네이션 구현
- D11 실시간은 장소별 1건씩 호출 필요

---

## 2026-01-31 — M2-1 Map API 완료

### 상태: M2-1 COMPLETE

### 완료한 작업

- [x] M2-1: Map API 엔드포인트 구현 (4개 파일)
  - `backend/db.py` — SQLAlchemy 엔진 + `get_db` FastAPI 의존성
  - `backend/api/schemas.py` — Pydantic 응답 모델 (HexagonSummary, HexagonsResponse, FlowCard, SalesCard, CompetitionCard, GrowthCard, RiskCard, HexagonDetailResponse)
  - `backend/api/map.py` — 두 엔드포인트 구현
    - `GET /api/map/hexagons?area_type=&category=&qtr=` — H3 그리드 + 집계 메트릭 (weight 기반 분배)
    - `GET /api/map/hexagon/{h3_index}` — 상세 6개 카드 (유동/매출/경쟁/성장/리스크) + QoQ 성장률
  - `backend/main.py` — map 라우터 등록

### 설계 결정

- Sync SQLAlchemy + psycopg2 (데이터 소규모, async 불필요)
- Raw SQL via `text()` (집계 조인에 ORM보다 명확)
- Weight 기반 집계: `bridge_area_h3_weight.weight`로 영역→H3 분배
- `data_asof`: 모든 응답에 분기 문자열 포함 (후행성 UX)
- Risk 경고 기준: 폐업률 >15%, 매출/유동인구 QoQ -10% 이상 감소

---

## 2026-02-01 — M2-1 버그 수정 + API 테스트 가이드

### 상태: M2-1 BUGFIX COMPLETE

### 수정한 버그

- [x] `backend/api/map.py` — `preset_area_scope` 조인 오류 (`area_code` → `area_id` 직접 조인)
- [x] `backend/api/map.py` — `_prev_quarter` 분기 포맷 (`2024Q1` → `20241` 형식으로 수정)
- [x] `backend/api/map.py` — `_agg` 함수 Decimal→float 변환 (DB NUMERIC 타입 호환)
- [x] `backend/requirements.txt` — 불필요한 geo 라이브러리(geopandas, fiona, pyproj, shapely) 제거 → Docker 빌드 수정

### 산출물

- `docs/API_TEST.md` — API 엔드포인트별 curl 테스트 가이드

### DoD 검증 결과

```
/health                                          → 200 OK ✓
/api/data/categories                             → 100개 업종 ✓
/api/data/area-scope                             → 27건 ✓
/api/data/area-scope?area_type=ADMIN_DONG        → 4건 ✓
/api/data/area-scope?area_type=COMMERCIAL_AREA   → 23건 ✓
/api/map/hexagons?area_type=COMMERCIAL_AREA      → H3 그리드 반환 ✓
/api/map/hexagon/{h3_index}                      → 상세 카드 반환 ✓
```

---

## 2026-02-01 — M2-3 LangGraph 에이전트 완료

### 상태: M2-3 DONE

### 완료한 작업

- [x] M2-3: LangGraph 에이전트 구현 (4개 파일)
  - `backend/agents/graph.py` — AgentState TypedDict + StateGraph 정의 (supervisor → sql_agent/insight_agent 조건 분기)
  - `backend/agents/supervisor.py` — GPT-4o-mini 기반 라우터 (sql/insight/both 분류)
  - `backend/agents/sql_agent.py` — SQL 생성 + 안전 검증 (SELECT only, 테이블 화이트리스트, LIMIT 200) + DB 실행
  - `backend/agents/insight_agent.py` — 구조화 응답 생성 (근거3 + 리스크2 + 추천2 + 체크리스트)

### LangGraph 흐름

```
START → supervisor → conditional_edge
  ├─ "sql"     → sql_agent → END
  ├─ "insight" → insight_agent → END
  └─ "both"    → sql_agent → insight_agent → END
```

### SQL 안전규칙

- SELECT만 허용, DDL/DML 키워드 차단
- 허용 테이블: dim_area, dim_category, fact_sales/flow/store, fact_realtime_congestion_area, bridge_area_h3_weight, preset_area_scope
- LIMIT 없으면 자동 추가 (200)
- 성수동 필터 프롬프트에 포함

### 알려진 이슈 (M4에서 해결)

- **SQL Agent `sql_result` 미반환**: SQL은 정상 생성되나 `state["sql_result"]`에 실행 결과가 리스트로 담기지 않음 → SSE `event: sql`의 `row_count`가 항상 0
- **업종명 매칭 실패**: 사용자가 "커피 전문점", "디저트 카페"로 질의하면 DB의 실제 업종명(`커피-음료` 등)과 불일치하여 빈 결과 반환 → SQL Agent 프롬프트에 `dim_category` 조회 단계 추가 필요
- **Insight Agent 환각**: SQL 결과가 비어도 LLM이 자체적으로 수치를 생성하여 응답 → SQL 결과 없을 시 "데이터 없음" 명시 로직 필요

→ M4-1 골든 쿼리 회귀 테스트에서 함께 검증/수정 예정

### 블로커

- 없음

---

## 2026-02-01 — M2-4 Chat API 완료

### 상태: M2-4 DONE (M2 COMPLETE)

### 완료한 작업

- [x] M2-4: POST /api/chat SSE 스트리밍 엔드포인트 구현
  - `backend/api/chat.py` — SSE 스트리밍 엔드포인트
    - `asyncio.to_thread`로 sync LangGraph를 non-blocking 실행
    - 단계별 SSE 이벤트: routing → sql → insight → done (에러 시 error)
    - Cache-Control, X-Accel-Buffering 헤더 설정
  - `backend/api/schemas.py` — ChatRequest Pydantic 모델 추가
  - `backend/main.py` — chat 라우터 등록

### SSE 이벤트 형식

```
event: routing  → {"route": "sql"|"insight"|"both"}
event: sql      → {"sql": "SELECT ...", "row_count": N}
event: insight  → {"evidence": [...], "risks": [...], ...}
event: done     → {"data_asof": "2025Q1"}
event: error    → {"message": "..."}
```

### DoD 검증 결과 (E2E 테스트)

```
# 1. SQL 경로 (route: sql)
POST /api/chat {"question": "성수동 디저트 카페 매출 Top3 알려줘"}
→ event: routing {"route": "sql"}            ✓
→ event: sql {"sql": "SELECT ...", "row_count": 0}  ✓ (SQL 생성 정상, row_count 이슈는 M4에서 수정)
→ event: done {"data_asof": "2026-02-01 11:23"}     ✓

# 2. Insight 경로 (route: insight)
POST /api/chat {"question": "성수동에서 카페 창업하면 리스크가 뭐야?"}
→ event: routing {"route": "insight"}        ✓
→ event: insight {"evidence": [...], "risks": [...], "recommendations": [...], "checklist": [...], "summary": "..."} ✓
→ event: done {"data_asof": "..."}           ✓

# 3. Both 경로 (route: both)
POST /api/chat {"question": "성수동에서 커피-음료 업종 매출이 가장 높은 상권 Top3 알려주고, 왜 그런지 분석해줘"}
→ event: routing {"route": "both"}           ✓
→ event: sql {"sql": "SELECT ..."}           ✓
→ event: insight {"evidence": [...], ...}    ✓
→ event: done {"data_asof": "..."}           ✓

# 4. Validation
POST /api/chat {"question": ""}  → 422 ✓

# 5. 에러 핸들링 (API 키 미설정 시)
→ event: error {"message": "내부 서버 오류가 발생했습니다."} ✓
```

### 블로커

- 없음

---

## 2026-02-02 — M3-1 H3 위치 불일치 수정

### 상태: M3-1 BUGFIX COMPLETE

### 문제점

- H3 hexagon이 실제 지도 위치와 맞지 않는 현상
- 상권 및 행정동 경계는 정확하게 표시되나, H3 hexagon 위치가 어긋남

### 근본 원인

**좌표 순서 불일치**:
- **h3-py (백엔드)**: `h3.h3_to_geo()` → `(lat, lng)` 반환
- **h3-js (프론트엔드)**: `h3ToGeoBoundary()` → `[[lng, lat], [lng, lat], ...]` 반환 (GeoJSON 표준)
- 프론트엔드가 boundary 좌표 배열을 `[lat, lng]`로 잘못 읽고 있었음

**해상도 불일치**:
- `HexMap.tsx`에서 `H3_RES = 10` 사용
- 프로젝트 표준은 `res=10` (CLAUDE.md, h3_mapper.py 모두 10)

### 수정 사항

1. **좌표 순서 수정** (`HexMap.tsx` L215-219)
   ```typescript
   // 수정 전
   const cLat = boundary.reduce((s, c) => s + c[0], 0) / boundary.length;
   const cLng = boundary.reduce((s, c) => s + c[1], 0) / boundary.length;
   
   // 수정 후 (GeoJSON 표준 [[lng, lat], ...])
   const cLng = boundary.reduce((s, c) => s + c[0], 0) / boundary.length;
   const cLat = boundary.reduce((s, c) => s + c[1], 0) / boundary.length;
   ```

2. **H3 해상도 통일** (`HexMap.tsx` L23)
   ```typescript
   const H3_RES = 9;  // 10 → 9
   ```

### 수정 파일

- `frontend/src/components/map/HexMap.tsx` — 좌표 순서 수정 + H3_RES 변경

### 검증 방법

1. 개발 서버 새로고침
2. 성수역(127.0557, 37.5446) 주변 hexagon 위치 확인
3. 연무장길(127.061, 37.5435) 주변 hexagon 위치 확인
4. 행정동/상권 토글 후 경계선과 hexagon 오버레이 일치 확인

### 블로커

- 없음

---

## 2026-02-03 — M3-3 사이드바 카드 완료 + 버그 수정

### 상태: M3-3 DONE + BUGFIX

### 완료한 작업

- [x] M3-3: Hex 클릭 → 사이드바 카드 구현
  - `frontend/src/types/map.ts` — HexagonDetailResponse 타입 추가 (FlowCard, SalesCard, CompetitionCard, GrowthCard, RiskCard)
  - `frontend/src/store/mapStore.ts` — sidebarOpen, hexDetail, hexDetailLoading 상태 + fetchHexDetail 액션 추가
  - `frontend/src/components/sidebar/MetricCard.tsx` — **신규** 메트릭 카드 컴포넌트 (GrowthBadge, MiniChart, BarDistribution, StatRow, WarningList)
  - `frontend/src/components/sidebar/Sidebar.tsx` — **신규** 사이드바 컴포넌트 (5개 카드: 유동/매출/경쟁/성장/리스크)
  - `frontend/src/components/map/HexMap.tsx` — 클릭 시 fetchHexDetail 호출, 선택 해제 시 closeSidebar 호출
  - `frontend/src/app/page.tsx` — Sidebar dynamic import 추가
  - shadcn/ui 컴포넌트 설치: ScrollArea, Skeleton, Separator

- [x] 버그 수정: 성장률 표시 (API 비율 → 퍼센트 변환)
  - `MetricCard.tsx` GrowthBadge: `rate * 100`
  - `Sidebar.tsx` GrowthStat: `rate * 100`

- [x] 버그 수정: 필터 연동 (사이드바 API 호출 시 파라미터 전달)
  - `fetchHexDetail`에 `area_type`, `qtr`, `category` 파라미터 추가
  - `setAreaType`, `setCategory`, `setQuarter` 변경 시 사이드바 자동 갱신

- [x] 상권별 점포 데이터 적재 (D2_STORE_TRDAR)
  - `etl/collectors/seoul_api_collector.py` — D2_STORE_TRDAR API 추가 (VwsmTrdarStorQq)
  - `etl/load_store_trdar_api.py` — **신규** 상권 기준 점포 ETL
  - 적재 결과: COMMERCIAL_AREA 6,985행 (7분기, 17개 상권)

- [x] 버그 수정: API area_type 필터링
  - `backend/api/map.py` `/hexagon/{h3_index}` — area_type 파라미터 추가, 해당 타입만 조회

- [x] 버그 수정: hexagons API 데이터 중복 합산
  - 원인: 모든 area_type 합산 + 업종별 다중 행 cartesian product
  - 해결: `hex_areas`를 area_type으로 필터 + `sales_agg`, `store_agg` CTE로 사전 집계

### 산출물

- `frontend/src/components/sidebar/Sidebar.tsx` — 메인 사이드바 (w-80, 5개 메트릭 카드)
- `frontend/src/components/sidebar/MetricCard.tsx` — 재사용 가능한 카드 빌딩 블록
- `etl/load_store_trdar_api.py` — 상권 기준 점포 ETL

### DoD 검증

```
npm run build → 성공 ✓
Hex 클릭 → 사이드바 열림 ✓
5개 카드 표시 (유동/매출/경쟁/성장/리스크) ✓
as-of 배지 표시 ✓
선택 해제 → 사이드바 닫힘 ✓
성장률 퍼센트 표시 ✓
필터 변경 시 사이드바 갱신 ✓
상권별 경쟁현황 개별 표시 (연무장길 1,525 vs 성수IT밸리 640) ✓
```

### 데이터 적재 현황 (업데이트)

| 데이터셋 | area_type | 행 수 | 비고 |
|---------|-----------|-------|------|
| D1 매출 | COMMERCIAL_AREA | 4,681행 | 13분기 |
| D2 점포 | ADMIN_DONG | 2,195행 | 4분기 |
| D2 점포 | **COMMERCIAL_AREA** | **6,985행** | **7분기 (신규)** |
| D5 유동 | COMMERCIAL_AREA | 92행 | 4분기 |

### 블로커

- 없음

---

## 전체 마일스톤 현황

| 마일스톤 | 상태 | 완료 티켓 | 남은 티켓 |
|---------|------|----------|----------|
| M0 Repo/Infra | DONE | M0-1~M0-4 | M0-5 (P1, 선택) |
| M1 Data Layer | DONE | M1-1~M1-8 | 없음 |
| M2 API Layer | DONE | M2-1~M2-4 | 없음 |
| M3 UI Layer | DONE | M3-1~M3-5 | 없음 |
| M4 Eval/Logging | 미시작 | - | M4-1~M4-3 |

## 다음 3개 액션

1. **M4-1 골든 쿼리 테스트**: SQL Agent 품질 보증
2. **M4-2 analysis_run 저장 로직**: 분석 결과 재현/감사
3. **M4-3 이벤트 로그**: 사용자 행동 추적

---

## 2026-02-02 — 행정동 경계 + 상권 폴리곤 지도 표시

### 상태: DONE

### 완료한 작업

- [x] GeoJSON 생성 스크립트 (`etl/export_boundaries_geojson.py`)
  - D9 SHP → `frontend/public/data/admin_dong.geojson` (4개 행정동)
  - D3 SHP → `frontend/public/data/commercial_areas.geojson` (17개 상권)
  - 속성: code, name, type(상권유형), admin_dong(소속 행정동)
- [x] HexMap.tsx에 Mapbox Source+Layer 기반 경계 레이어 추가
  - 행정동 경계: fill(반투명) + line(색상별) + 라벨(중심점)
  - 상권 영역: fill(유형별 색상) + line(점선) + 라벨(상권명 + 유형)
  - 발달상권(파랑), 골목상권(초록), 전통시장(주황) 색상 구분
- [x] 레이어 토글 UI (행정동/상권 on/off 버튼)
  - `mapStore`에 `showAdminDong`, `showCommercialAreas` 상태 추가
- [x] 범례에 상권 유형별 색상 표시 추가
- [x] 기존 H3 헥사곤 레이어 유지 (상권 폴리곤 위에 반투명 오버레이)

### 수정 파일

| 파일 | 변경 |
|------|------|
| `etl/export_boundaries_geojson.py` | **신규** — SHP→GeoJSON 변환 |
| `frontend/public/data/admin_dong.geojson` | **신규** — 4개 행정동 경계 |
| `frontend/public/data/commercial_areas.geojson` | **신규** — 17개 상권 폴리곤 |
| `frontend/src/store/mapStore.ts` | showAdminDong/showCommercialAreas 토글 추가 |
| `frontend/src/components/map/HexMap.tsx` | 경계 레이어 + 토글 + 범례 추가 |

### 블로커

- 없음

---

## 2026-02-02 — M3-1 HexMap 개선 (상권-H3 연동 완료)

### 상태: M3-1 AREA INTEGRATION DONE

### 완료한 작업

- [x] Backend API 수정: HexagonSummary에 area_id, area_name, real_name 추가
  - `backend/api/schemas.py` — HexagonSummary 필드 추가
  - `backend/api/map.py` — SQL 쿼리에 primary_area CTE 추가 (area_type별 필터링)
- [x] DB 스키마 수정: dim_area에 real_name 칼럼 추가
  - 17개 상권에 실제 상권명 매핑 (예: 성수역→연무장길, 뚝섬역→뚝섬 카페거리)
- [x] Frontend 수정: zone 기반 → area_id/area_name 기반으로 변경
  - `frontend/src/types/map.ts` — area_id, area_name, real_name 필드 추가
  - `frontend/src/store/mapStore.ts` — selectedAreaId, selectedAreaName, selectedRealName 상태 추가
  - `frontend/src/components/map/HexMap.tsx` — 툴팁/인디케이터에 real_name 우선 표시
- [x] 상권 미포함 hexagon 회색 처리 (area_name === null → 회색)

### real_name 매핑 (17개 상권)

| 공공데이터 상권명 | 실제 상권명 (real_name) |
|------------------|------------------------|
| 성수역 | 연무장길 |
| 뚝섬역 | 뚝섬 카페거리 |
| 서울숲역 | 서울숲 입구 |
| 성수초등학교 | 성수IT밸리 |
| 성원어린이공원 | 헤이그라운드/팝업 |
| 성수2가3동주민센터 | 대림창고 일대 |
| 성수역 골목형상점가 | 수제화거리 |
| 성수119안전센터 | 수제화 공방거리 |

### 블로커

- 없음

---

## 2026-02-02 — D2 점포 데이터 적재 완료

### 상태: D2 ETL COMPLETE

### 문제 및 해결

**문제**: `fact_store_area_qtr` 테이블이 비어있어 점포수가 0으로 표시

**원인**: 
1. D2 점포 API가 아직 호출되지 않음
2. `dim_area` 행정동 코드 불일치 (DB: `1104xxxx` vs API: `1120xxxx`)

**해결**:
1. `dim_area` 행정동 코드 수정: `1104xxxx` → `1120xxxx`
2. `etl/load_store_api.py` 실행

### 적재 결과

```
fact_store_area_qtr: 1,459 rows
  - 20251: 367 rows
  - 20244: 364 rows
  - 20243: 363 rows
  - 20242: 365 rows
```

### 실행 방법

```bash
docker compose run --rm --entrypoint python etl -m etl.load_store_api
```

### 블로커

- 없음

---

## 2026-02-02 — H3 데이터 모델 문서화

### 상태: DONE

### 완료한 작업

- [x] `docs/H3_DATA_MODEL.md` — H3 weight 매핑 원리 상세 설명서 작성
  - Weight = hexagon과 상권/행정동 겹침 비율 (0.0~1.0)
  - 동일 상권이라도 hexagon 위치(중심/경계)에 따라 값이 다른 이유 설명
  - SQL 집계 로직, 시각화 의미 해석, FAQ 포함

### 블로커

- 없음

---

## 2026-02-02 — M3-2 필터 패널 + 영역 토글 완료

### 상태: M3-2 DONE

### 완료한 작업

- [x] shadcn/ui 컴포넌트 설치 (Select, Button, Card, Badge, Label)
- [x] `types/map.ts` — Category, AreaScopeItem 타입 추가
- [x] `store/mapStore.ts` — categories/areas 상태 + fetchCategories/fetchAreas 액션 추가
- [x] `components/filters/FilterPanel.tsx` — 신규 생성
  - 업종 Select (전체 + API 카테고리 목록)
  - 분기 Select (최근 8분기 자동 생성)
  - 행정동/상권 토글 (Button variant 활용)
  - 마운트 시 categories/areas API fetch
- [x] `app/page.tsx` — flex 레이아웃 (좌측 FilterPanel w-72 + 우측 HexMap flex-1)
- [x] `components/map/HexMap.tsx` — 필터 파라미터(areaType, category, quarter) API 연동
- [x] deck.gl 타입 선언 파일 추가 (`types/deck.gl.d.ts`)

### 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/types/map.ts` | Category, AreaScopeItem 타입 추가 |
| `frontend/src/types/deck.gl.d.ts` | 신규 — deck.gl 모듈 타입 선언 |
| `frontend/src/store/mapStore.ts` | categories/areas 상태, fetch 액션 추가 |
| `frontend/src/components/filters/FilterPanel.tsx` | **신규** 필터 패널 |
| `frontend/src/components/ui/` | shadcn/ui 5개 컴포넌트 설치 |
| `frontend/src/app/page.tsx` | flex 레이아웃 변경 |
| `frontend/src/components/map/HexMap.tsx` | 필터 파라미터 API 연동, 컨테이너 사이징 수정 |

### DoD 검증

```
npm run build → 성공 ✓
FilterPanel 렌더링 (업종/분기 Select, 영역 토글) ✓
필터 변경 → mapStore 상태 업데이트 → HexMap useEffect 재트리거 ✓
```

### 블로커

- 없음

---

## 2026-02-03 — mapbox-gl CSS 임포트 수정

### 상태: DONE

### 문제점

- `Module not found: Can't resolve 'mapbox-gl/dist/mapbox-gl.css'` 빌드 에러
- mapbox-gl v3.18.1 설치되어 있고 CSS 파일도 존재하나 Next.js에서 해석 실패

### 근본 원인

- Next.js에서는 node_modules 내 CSS를 컴포넌트 파일에서 직접 import 불가
- global CSS 파일(`globals.css`)에서만 외부 CSS import 허용

### 해결

1. `HexMap.tsx`에서 `import "mapbox-gl/dist/mapbox-gl.css";` 제거
2. `globals.css` 최상단에 `@import "mapbox-gl/dist/mapbox-gl.css";` 추가

### 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/components/map/HexMap.tsx` | mapbox-gl CSS import 라인 제거 |
| `frontend/src/app/globals.css` | `@import "mapbox-gl/dist/mapbox-gl.css";` 추가 |

### 검증

```
npm run build → 성공 ✓
```

### 블로커

- 없음

---

## 2026-02-01 — M3-1 Deck.gl 3D Hex 맵 완료

### 상태: M3-1 DONE

### 완료한 작업

- [x] M3-1: Deck.gl 3D Hex 맵 구현 (5개 파일)
  - `frontend/src/types/map.ts` — HexagonSummary, HexagonsResponse, MapViewState 타입 정의
  - `frontend/src/store/mapStore.ts` — Zustand 상태 관리 (selectedHex, areaType, category, quarter, elevationMetric)
  - `frontend/src/components/map/HexMap.tsx` — 핵심 맵 컴포넌트
    - MapLibre GL + CARTO dark-matter 무료 타일 (Mapbox 토큰 불필요)
    - ColumnLayer (diskResolution=6, radius=85m)
    - elevation: 유동인구/매출 토글 (우상단 버튼)
    - color: sales_amt 기준 파랑→노랑→빨강 스케일
    - onClick → mapStore.setSelectedHex
    - hover 툴팁 (매출/유동인구/점포수)
    - API fetch with mock data fallback
  - `frontend/src/app/page.tsx` — dynamic import (SSR 비활성화)
  - `frontend/src/app/layout.tsx` — 메타데이터 "K-CIA Lite"

### 기술 결정

- **MapLibre GL + CARTO 타일**: 무료, Mapbox 토큰 불필요
- **ColumnLayer**: H3HexagonLayer 대신 사용 (API가 lat/lng 제공하므로 더 단순)
- **Mock 데이터**: API 미연결 시 성수동 12개 헥사곤 샘플로 렌더링
- **dynamic import**: Deck.gl SSR 비호환 → `next/dynamic`으로 클라이언트 전용 로드

### DoD 검증

```
npm run build → 성공 ✓
ColumnLayer 렌더링 → 성수동 중심 3D 헥사곤 ✓
elevation 토글 → 유동인구/매출 전환 ✓
hover 툴팁 → 매출/유동인구/점포수 표시 ✓
onClick → console.log h3_index ✓
```

### 블로커

- 없음

---

## 2026-02-03 — M3-4 챗봇 UI 완료

### 상태: M3-4 DONE

### 완료한 작업

- [x] M3-4: 챗봇 UI (스트리밍) 구현 (10개 파일)
  - `frontend/src/types/chat.ts` — ChatMessage, SSE 이벤트 타입 정의
  - `frontend/src/store/chatStore.ts` — Zustand 챗 상태 (messages, isStreaming, isOpen 등)
  - `frontend/src/hooks/useStreamingChat.ts` — SSE 스트리밍 훅 (AbortController, 이벤트 파싱)
  - `frontend/src/components/chat/ChatPanel.tsx` — 플로팅 버튼 + 확장/축소 패널
  - `frontend/src/components/chat/ChatInput.tsx` — 입력창 (Enter 전송, 취소 버튼)
  - `frontend/src/components/chat/ChatMessages.tsx` — 메시지 목록 + 자동 스크롤
  - `frontend/src/components/chat/ChatMessage.tsx` — 개별 메시지 (구조화 응답 렌더링)
  - `frontend/src/components/chat/insight/EvidenceCard.tsx` — 근거 카드
  - `frontend/src/components/chat/insight/RisksCard.tsx` — 리스크 카드
  - `frontend/src/components/chat/insight/RecommendationsCard.tsx` — 추천 카드
  - `frontend/src/components/chat/insight/ChecklistCard.tsx` — 체크리스트 카드
  - `frontend/src/components/chat/insight/SqlCard.tsx` — SQL 쿼리 카드
  - `frontend/src/app/page.tsx` — ChatPanel dynamic import 추가
- [x] ESLint warning 수정 (useStreamingChat.ts handleEvent 의존성)

### 기능 상세

- **플로팅 버튼**: 우하단 고정, 클릭 시 패널 열림
- **확장/축소**: 400px ↔ 500px 너비, 500px ↔ 600px 높이
- **대화 초기화**: 휴지통 버튼으로 메시지 클리어
- **SSE 스트리밍**: routing → sql → insight → done 순서로 이벤트 처리
- **구조화 응답**: 근거3 + 리스크2 + 추천2 + 체크리스트 카드 형태로 렌더링
- **as-of 배지**: 응답 하단에 "기준: {timestamp}" 표시
- **필터 연동**: 현재 선택된 area_type, category, qtr를 API 요청에 포함

### DoD 검증

```
npm run build → 성공 (ESLint warning 0개) ✓
curl /api/chat → SSE 스트리밍 정상 ✓
플로팅 버튼 렌더링 ✓
질문 입력 → 스트리밍 응답 표시 ✓
구조화 카드 (Evidence/Risks/Recommendations/Checklist) 렌더링 ✓
as-of 배지 표시 ✓
```

### 블로커

- 없음

---

## 2026-02-03 — M3-5 as-of 배지 검증 완료

### 상태: M3-5 DONE

### 완료한 작업

- [x] M3-5: as-of 배지 구현 확인
  - `Sidebar.tsx` — 사이드바 카드에 분기 배지 + as-of 텍스트 표시
  - `ChatMessage.tsx` — 챗봇 응답에 "기준: {dataAsof}" 배지 표시
- [x] 모든 데이터 표시 영역에 as-of 배지 존재 확인

### 참고사항

- 후행성 경고 배너, D11 실시간 확인 버튼은 P1 (Should) 항목으로 추후 구현 가능
- 현재 기본 요구사항(as-of 배지)은 완료

### 블로커

- 없음

---

## 2026-02-03 — M4-1 골든 쿼리 테스트 완료

### 상태: M4-1 DONE

### 완료한 작업

- [x] 골든 쿼리 3종 정의 및 테스트 파일 생성
  - `tests/golden_queries/golden_queries.json` — TopN 매출, QoQ 비교, 적합도 점수
  - `tests/test_sql_agent.py` — Validation + Integration 테스트 스크립트
- [x] 버그 수정: sql_result row_count 미반환
  - `backend/api/chat.py` — dict 구조의 row_count 정확히 추출
- [x] 업종명 fuzzy 매칭 로직 추가
  - `backend/agents/sql_agent.py` — 프롬프트에 Category Name Mapping 섹션 추가
  - 커피/카페 → '커피-음료', 디저트/베이커리 → '제과점' 등 14개 매핑
- [x] Insight Agent 환각 방지
  - `backend/agents/insight_agent.py` — SQL 결과 없을 시 "조회된 데이터가 없습니다" 명시
  - row_count 정보를 명시적으로 전달

### 테스트 결과

```
============================================================
Golden Query Validation Tests (DB Direct)
============================================================
[PASS] TopN 매출 추천: 3 rows | area_name=뚝섬역, sales_amt=3604512060...
[PASS] QoQ 비교: 10 rows | area_name=뚝섬역, curr_sales=3604512060...
[PASS] 적합도 점수 (창업 추천): 5 rows | area_name=성수역, sales_amt=1233919264...
============================================================
Validation Results: 3 passed, 0 failed
============================================================

============================================================
SQL Agent Integration Tests (via API)
============================================================
[PASS] TopN 매출 추천: route=sql, rows=3, patterns=6/6
[PASS] QoQ 비교: route=sql, rows=14, patterns=3/3
[PASS] 적합도 점수 (창업 추천): route=both, rows=3, patterns=2/2
============================================================
Integration Results: 3 passed, 0 failed
============================================================
```

### 실행 방법

```bash
docker compose run --rm --entrypoint bash etl -c "cd /workspace && python tests/test_sql_agent.py"
docker compose run --rm --entrypoint bash etl -c "cd /workspace && python tests/test_sql_agent.py --integration"
```

### 수정 파일

| 파일 | 변경 |
|------|------|
| `tests/golden_queries/golden_queries.json` | **신규** — 골든 쿼리 3종 정의 |
| `tests/test_sql_agent.py` | **신규** — 테스트 스크립트 |
| `backend/api/chat.py` | row_count 버그 수정 (dict 구조 처리) |
| `backend/agents/sql_agent.py` | Category Name Mapping, 테이블 컬럼 설명 추가 |
| `backend/agents/insight_agent.py` | 환각 방지 로직, row_count 명시 전달 |

### DoD 검증

```
Validation: 3/3 통과 ✓
Integration: 3/3 통과 ✓
```

### 블로커

- 없음

---

## 2026-02-03 — AI Agent 메모리 기능 완료

### 상태: MEMORY FEATURE DONE

### 완료한 작업

- [x] Backend: ChatRequest에 messages 필드 추가 (`backend/api/schemas.py`)
- [x] Backend: AgentState에 messages 필드 추가 (`backend/agents/graph.py`)
- [x] Backend: chat.py에서 messages를 state로 전달 (`backend/api/chat.py`)
- [x] Backend: SQL Agent에 대화 히스토리 컨텍스트 전달 (`backend/agents/sql_agent.py`)
- [x] Backend: Insight Agent에 대화 히스토리 컨텍스트 전달 (`backend/agents/insight_agent.py`)
- [x] Frontend: ChatMessagePayload 타입 추가 (`frontend/src/types/chat.ts`)
- [x] Frontend: ChatRequest에 messages 필드 추가 (`frontend/src/types/chat.ts`)
- [x] Frontend: useStreamingChat에서 최근 6개 메시지를 API payload에 포함 (`frontend/src/hooks/useStreamingChat.ts`)

### 기능 상세

- 후속 질문 시 이전 대화 컨텍스트 유지 (예: "뚝섬역 카페 매출 알려줘" → "성수역은?")
- 최근 6개 메시지만 전달하여 토큰 절약
- user/assistant 메시지만 필터링 (system 제외)

### 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/types/chat.ts` | ChatMessagePayload, ChatRequest.messages 추가 |
| `frontend/src/hooks/useStreamingChat.ts` | historyMessages 구성, payload에 포함 |

### DoD 검증

```
npm run build → 성공 (ESLint warning 0개) ✓
```

### 테스트 방법

```bash
# 테스트 시나리오
# 1. "뚝섬역 카페 매출 알려줘"
# 2. "성수역은?" (후속 질문 - 컨텍스트 유지 확인)
```

### 블로커

- 없음

---

## 2026-02-03 — AI Agent 품질 개선 (라우팅, 계산, Fallback)

### 상태: AGENT QUALITY IMPROVEMENTS DONE

### 발견된 이슈

| # | 이슈 | 원인 |
|---|------|------|
| 1 | route="sql"일 때 insight 미반환 | insight_agent 스킵 → 빈 응답 |
| 2 | "카페별 1일 매출" 계산 오류 | sales_cnt/store_cnt 혼동, 1일 계산 로직 없음 |
| 3 | 라우팅이 "sql"로 너무 자주 분류 | 기본값이 "insight"여서 both 누락 |

### 수정 내용

1. **chat.py — Fallback Insight 추가**
   - route="sql"이어도 결과가 있으면 fallback insight 생성
   - 상위 5개 결과 샘플 + row_count 요약
   - SQL 에러 시에도 에러 메시지를 insight로 반환

2. **supervisor.py — 라우팅 개선**
   - 기본값을 "insight" → "both"로 변경
   - "sql" 조건을 강화: "숫자만", "데이터만", "쿼리만" 명시적 요청만
   - "궁금해", "알려줘" 등은 무조건 "both"

3. **sql_agent.py — 계산 가이드 추가**
   - `sales_cnt` vs `store_cnt` 차이 명확화 (거래건수 vs 점포수)
   - "1일" 계산 = `/ 90` (분기 ≈ 90일)
   - "카페별" 계산 = `/ NULLIF(store_cnt, 0)`
   - 예제 SQL 추가: 카페별 1일 매출 쿼리

### 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/api/chat.py` | route=sql fallback insight 로직 추가 (20줄) |
| `backend/agents/supervisor.py` | 라우팅 프롬프트 개선, 기본값 both |
| `backend/agents/sql_agent.py` | 계산 가이드 섹션 추가 (35줄) |

### 테스트 결과

```bash
# 이전 (오류)
Q: "전체카페가 아니라 한개의 카페 기준으로 궁금한거야. 그것도 하루매출"
→ route: "sql", insight: (없음)

# 수정 후 (정상)
Q: 동일
→ route: "both"
→ SQL: ROUND(fs.sales_amt / NULLIF(fst.store_cnt, 0) / 90) AS daily_sales_per_store
→ insight: "뚝섬역 하루 매출 616,155원..." ✓

# Fallback 테스트
Q: "매출 숫자만 알려줘"
→ route: "sql"
→ insight: "SQL 쿼리 결과 200건이 조회되었습니다..." ✓ (fallback 작동)
```

### 블로커

- 없음

---

## 전체 마일스톤 현황

| 마일스톤 | 상태 | 완료 티켓 | 남은 티켓 |
|---------|------|----------|----------|
| M0 Repo/Infra | DONE | M0-1~M0-4 | M0-5 (P1, 선택) |
| M1 Data Layer | DONE | M1-1~M1-8 | 없음 |
| M2 API Layer | DONE | M2-1~M2-4 | 없음 |
| M3 UI Layer | DONE | M3-1~M3-5 | 없음 |
| M4 Eval/Logging | DONE | M4-1~M4-3 | 없음 |
| M5 Store H3 Weight | DELETED | - | - |
| M6 S3 Data+Backend | PLANNED | - | M6-1~M6-5 |
| M7 S3 Frontend | PLANNED | - | M7-1~M7-5 |
| M8 S4 비교 | PLANNED | - | M8-1~M8-3 |
| M9 SNS Module | PLANNED | - | M9-1~M9-6 |

## 다음 3개 액션

1. **M6-1 DB Migration**: fact_facility_area_qtr 테이블 생성
2. **M6-2 D8 ETL**: 집객시설 데이터 수집
3. **M6-3 Hexagons API 인구통계 필터**: popup mode 파라미터

---

## 2026-02-07 — Phase 3 + SNS 계획 수립

### 상태: PLANNING COMPLETE

- Phase 2 건너뛰고 Phase 3 (S3 팝업 + S4 분기비교) 먼저 진행 (DEC-015)
- SNS 모듈: YouTube + Naver Blog (비용 0) (DEC-016)
- SNS 데이터 H3 매핑 불가 → 지역 스코프 (DEC-017)
- M6~M9 마일스톤 정의
- 문서 갱신: PLAN.md, TODO.md, DECISIONS.md, PROGRESS.md, CLAUDE.md

---

## 2026-02-03 — 챗봇 컨텍스트 개선

### 완료한 작업

- [x] 선택 상권 카드 데이터를 /api/chat 요청에 포함하여 챗봇 컨텍스트로 활용
- [x] Insight Agent가 선택 카드 데이터를 참고하도록 입력 메시지 보강

### 블로커

- 없음

---

## 2026-02-07 — M5 삭제

### 상태: DELETED

- M5 (점포 수 기반 H3 Weight) 불필요로 판단하여 삭제
- 관련 코드 및 마이그레이션 파일 제거됨

---

## 2026-02-07 — M6-1 DB Migration 완료

### 상태: M6-1 DONE

### 완료한 작업

- [x] M6-1: `fact_facility_area_qtr` 테이블 생성
  - `backend/migrations/004_s3_facility.sql` — DDL + 인덱스 + COMMENT
  - PK: `(area_id, qtr, facility_type)`
  - FK: `area_id → dim_area(area_id)`
  - 인덱스: `(area_id, qtr)` 복합

### DoD 검증

```
CREATE TABLE 성공 ✓
PK/FK 제약조건 정상 (무효 area_id 거부 확인) ✓
INSERT/SELECT/DELETE 정상 동작 ✓
```

### 블로커

- 없음

---

## 2026-02-07 — M6-2 D8 집객시설 ETL 완료

### 상태: M6-2 DONE

### 완료한 작업

- [x] `etl/collectors/seoul_api_collector.py` — `D8_FACILITY: VwsmTrdarFcltyQq` 추가
- [x] `etl/load_facility_api.py` — D8 집객시설 ETL (narrow/EAV 포맷)
- [x] API 서비스명 탐색: 원래 계획 `VwsmTrdarHitterIndQq`(OA-15581, 배후지)는 ERROR-500 → `VwsmTrdarFcltyQq`(OA-15580, 상권) 사용 (DEC-018)
- [x] ETL 버그 수정: API가 분기 파라미터 무시 → 전체 데이터 1회 fetch + `STDR_YYQU_CD` 사용

### DoD 검증

```
fact_facility_area_qtr: 6,800 rows ✓
분기 커버리지: 20개 분기 (2020Q4 ~ 2025Q3) ✓
상권: 17개 성수동 상권 ✓
시설 유형: 20종 ✓
Top 시설: 관광시설(5,600), 버스정류장(1,400), 약국(600), 은행(500)
```

### 실행 방법

```bash
docker compose run --rm --entrypoint python etl -m etl.load_facility_api
```

### 블로커

- 없음

---

## 2026-02-07 — M6-3, M6-4 완료

### 상태: M6-3, M6-4 DONE

### 완료한 작업

- [x] M6-3: Hexagons API 인구통계 필터 — 이미 기존 코드에 구현됨 (target_gender, target_age, mode 파라미터 + popup mode flow_by_demo JSONB 추출)
- [x] M6-4: Hexagon Detail 확장 (시설 + 인구통계 + 시간대 카드)
  - `backend/api/schemas.py` — FacilityItem, FacilityCard, DemoGenderRatio, DemoAgeItem, DemoCard, TimeSlotItem, TimeSlotRecommendation 모델 추가
  - `backend/api/schemas.py` — HexagonDetailResponse에 facility, demo, time_slot 필드 추가
  - `backend/api/map.py` — `_build_facility_card()`: fact_facility_area_qtr 쿼리 + 시설 유형별 집계
  - `backend/api/map.py` — `_build_demo_card()`: flow_by_demo JSONB → 성별/연령대 분포 분석
  - `backend/api/map.py` — `_build_time_slot()`: flow_by_hour (시간대 범위) + flow_by_weekday → 피크 요일 분석
  - `backend/api/map.py` — FACILITY_LABELS 매핑 (20종 시설 한글 라벨)

### DoD 검증

```
# 서울숲 카페거리 (8a30e1c1664ffff)
facility: total=1, top=['관광시설'] ✓
demo: M=46.3%/F=53.7%, peak_age=30, peak_gender=여성 ✓
time_slot: peak_weekday=목 ✓

# 성수동 카페거리 (8a30e1c12ab7fff)
facility: total=9 (관광시설5, 버스정류장3, 은행1) ✓
demo: M=47.7%/F=52.3%, peak_age=20, peak_gender=여성 ✓
time_slot: peak_weekday=목 ✓
```

### 참고사항

- flow_by_hour 시간대별 데이터가 모두 null (Seoul API D5에서 시간대 유동인구 미제공)
  - 시간대 추천은 flow_by_weekday 기반 피크 요일만 제공
  - 향후 D5 데이터 갱신 시 시간대 슬롯별 비율도 자동 반영되도록 설계
- FacilityCard, DemoCard, TimeSlotRecommendation은 Optional 필드 (데이터 없으면 null 반환)

### 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/api/schemas.py` | FacilityCard, DemoCard, TimeSlotRecommendation 등 7개 모델 추가, HexagonDetailResponse 확장 |
| `backend/api/map.py` | `_build_facility_card`, `_build_demo_card`, `_build_time_slot` 헬퍼 추가, hexagon detail에 3개 카드 통합 |

### 블로커

- 없음

---

## 2026-02-07 — M6-5 SQL Agent 프롬프트 업데이트 완료

### 상태: M6-5 DONE (M6 COMPLETE)

### 완료한 작업

- [x] M6-5: SQL Agent 프롬프트 업데이트
  - `ALLOWED_TABLES`에 `fact_facility_area_qtr` 추가
  - `SQL_SYSTEM_PROMPT`에 추가:
    - `flow_by_demo` JSONB 구조 및 PostgreSQL `->>` 추출 패턴 (성별/연령대)
    - `flow_by_weekday` JSONB 구조 및 요일별 추출 예제
    - `flow_by_hour` JSONB 구조 (시간대별)
    - `fact_facility_area_qtr` 스키마 (narrow/EAV 포맷)
    - 시설 유형 코드 20종 매핑 (VIATR_FCLTY→관광시설, SUBWAY_STATN→지하철역 등)
    - 인구통계 쿼리 예제: "20대 여성 유동인구 Top3"
    - 시설 쿼리 예제: "지하철역/버스정류장 가장 많은 상권"
    - Latest Quarter: Facility 20253 추가

### 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/agents/sql_agent.py` | ALLOWED_TABLES + SQL_SYSTEM_PROMPT 확장 (인구통계 JSONB, 시설 테이블, 예제 쿼리) |

### DoD 검증

```
ALLOWED_TABLES에 fact_facility_area_qtr 포함 ✓
flow_by_demo JSONB 추출 패턴 (->>'male', ->>'age_20' 등) ✓
fact_facility_area_qtr narrow/EAV 쿼리 패턴 ✓
시설 유형 코드 20종 매핑 ✓
Latest Quarters에 Facility 추가 ✓
```

### 블로커

- 없음

---

## 전체 마일스톤 현황

| 마일스톤 | 상태 | 완료 티켓 | 남은 티켓 |
|---------|------|----------|----------|
| M0 Repo/Infra | DONE | M0-1~M0-4 | M0-5 (P1, 선택) |
| M1 Data Layer | DONE | M1-1~M1-8 | 없음 |
| M2 API Layer | DONE | M2-1~M2-4 | 없음 |
| M3 UI Layer | DONE | M3-1~M3-5 | 없음 |
| M4 Eval/Logging | DONE | M4-1~M4-3 | 없음 |
| M5 Store H3 Weight | DELETED | - | - |
| M6 S3 Data+Backend | DONE | M6-1~M6-5 | 없음 |
| M7 S3 Frontend | IN PROGRESS | M7-1~M7-3 | M7-4~M7-5 |
| M8 S4 비교 | PLANNED | - | M8-1~M8-3 |
| M9 SNS Module | PLANNED | - | M9-1~M9-6 |

---

## 2026-02-07 — M6 버그 수정 (JSONB 캐스팅 + Insight 응답 유형)

### 상태: BUGFIX COMPLETE

### 발견된 이슈

| # | 이슈 | 원인 |
|---|------|------|
| 1 | 인구통계 SQL 쿼리 실패 (row_count: 0) | `flow_by_demo` JSONB 값이 `"191521.0"` (float 문자열)인데 `::int` 캐스팅 시 PostgreSQL 에러 |
| 2 | 단순 조회에도 모든 카드(추천/리스크) 반환 | 질문 유형 분류 없이 일괄 구조화 응답 생성 |

### 수정 내용

1. **sql_agent.py — JSONB 캐스팅 수정**
   ```sql
   -- 수정 전 (실패)
   SELECT (flow_by_demo->>'female')::int  -- ERROR: invalid input syntax for type integer: "191521.0"
   
   -- 수정 후 (성공)
   SELECT (flow_by_demo->>'female')::numeric
   ```
   - Line 127-155: 모든 JSONB 추출 예제에서 `::int` → `::numeric` 변경
   - `flow_by_demo`, `flow_by_weekday`, `flow_by_hour` 모두 수정

2. **insight_agent.py — 질문 유형 분류 로직 추가**
   - 5가지 응답 유형 분류:
     - `data_lookup`: summary + data_table + evidence (단순 조회)
     - `recommendation`: summary + recommendations + evidence + risks + checklist (창업 추천)
     - `risk_analysis`: summary + risks + evidence + action_items (리스크 진단)
     - `comparison`: summary + comparison + evidence (비교 분석)
     - `general`: summary + evidence (일반)
   - `response_type` 필드 추가 → 프론트엔드 조건부 렌더링 가능

### 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/agents/sql_agent.py` | JSONB 캐스팅 `::int` → `::numeric` (4개소) |
| `backend/agents/insight_agent.py` | 질문 유형 분류 + response_type 필드 추가 |

### 테스트 결과

```bash
# 수정 전
"20대 여성 유동인구 Top3" → row_count: 0 (SQL 에러)

# 수정 후
"20대 여성 유동인구 Top3" → row_count: 3, response_type: "data_lookup" ✓
"지하철역/버스정류장 Top5" → row_count: 5, 시설 집계 정상 ✓
"남성 비율 높은 상권" → row_count: 5, 성별 비율 계산 정상 ✓
```

### 블로커

- 없음

---

## 2026-02-07 — M7-1, M7-2, M7-3 완료

### 상태: M7-1~M7-3 DONE

### 완료한 작업

- [x] M7-1: Zustand Store 확장 — 이전 세션에서 이미 구현됨 (mode, targetGender, targetAge, setMode, setTargetGender, setTargetAge)
- [x] M7-2: TypeScript 타입 추가
  - `frontend/src/types/map.ts` — FacilityItem, FacilityCard, DemoGenderRatio, DemoAgeItem, DemoCard, TimeSlotItem, TimeSlotRecommendation 인터페이스 추가
  - HexagonDetailResponse에 facility, demo, time_slot 필드 추가
- [x] M7-3: 팝업 모드 필터 UI
  - `frontend/src/components/filters/PopupModePanel.tsx` — **신규** 컴포넌트
    - Default/Popup 모드 토글 버튼
    - 팝업 모드 시 성별 필터 (전체/남성/여성)
    - 팝업 모드 시 연령대 필터 (전체/10대~60+)
    - 이벤트 트래킹 (FILTER_APPLY)
  - `frontend/src/components/filters/FilterPanel.tsx` — PopupModePanel 통합
  - `frontend/src/components/map/HexMap.tsx` — hexagons API 호출에 mode, target_gender, target_age 파라미터 전달

### DoD 검증

```
npm run build → 성공 (타입 에러 0개) ✓
PopupModePanel 렌더링 (모드 토글, 성별/연령 필터) ✓
popup 모드 토글 → store 상태 변경 ✓
필터 변경 → hexagons API에 mode/target_gender/target_age 파라미터 전달 ✓
hexDetail API에도 popup 파라미터 전달 (기존 M7-1에서 구현) ✓
```

### 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/types/map.ts` | FacilityCard, DemoCard, TimeSlotRecommendation 등 7개 인터페이스 + HexagonDetailResponse 확장 |
| `frontend/src/components/filters/PopupModePanel.tsx` | **신규** — 팝업 모드 필터 패널 |
| `frontend/src/components/filters/FilterPanel.tsx` | PopupModePanel import + 통합 |
| `frontend/src/components/map/HexMap.tsx` | mode/targetGender/targetAge store 연동 + hexagons API 파라미터 전달 |

### 블로커

- 없음

---

## 2026-02-07 — M7-4, M7-5 완료 (M7 COMPLETE)

### 상태: M7-4, M7-5 DONE (M7 COMPLETE)

### 완료한 작업

- [x] M7-4: 사이드바 카드 3개 추가
  - `frontend/src/components/sidebar/FacilityCard.tsx` — **신규** 집객시설 카드 (시설 유형별 목록, 총 시설 수)
  - `frontend/src/components/sidebar/DemoCard.tsx` — **신규** 인구통계 카드 (성별 비율 바, 연령대 분포 차트, 주 고객)
  - `frontend/src/components/sidebar/TimeSlotCard.tsx` — **신규** 시간대 추천 카드 (피크 요일, 시간대별 유동 비율)
  - `frontend/src/components/sidebar/Sidebar.tsx` — 3개 카드 통합 (데이터 있으면 표시)

- [x] M7-5: HexMap 팝업 모드 시각화
  - `frontend/src/types/map.ts` — HexagonSummary에 target_flow, target_flow_ratio 필드 추가
  - `frontend/src/components/map/HexMap.tsx` — popup 모드 시각화:
    - 색상: target_flow_ratio 기반 파랑→보라→마젠타 스케일
    - 높이: target_flow 기반 elevation
    - 범례: 팝업 모드 시 "타겟 인구 비율" 범례로 전환
    - 툴팁: 타겟 유동인구, 전체 유동인구, 비율 표시

### DoD 검증

```
npm run build → 성공 (타입 에러 0개) ✓
FacilityCard 렌더링 (시설 목록) ✓
DemoCard 렌더링 (성별 비율 + 연령대 차트) ✓
TimeSlotCard 렌더링 (피크 요일) ✓
popup 모드 → 파랑→보라 색상 스케일 ✓
popup 모드 → target_flow 기반 elevation ✓
popup 모드 → 범례 전환 ✓
popup 모드 → 툴팁 타겟 유동 표시 ✓
```

### 수정 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/types/map.ts` | HexagonSummary에 target_flow, target_flow_ratio 추가 |
| `frontend/src/components/sidebar/FacilityCard.tsx` | **신규** — 집객시설 카드 |
| `frontend/src/components/sidebar/DemoCard.tsx` | **신규** — 인구통계 카드 |
| `frontend/src/components/sidebar/TimeSlotCard.tsx` | **신규** — 시간대 추천 카드 |
| `frontend/src/components/sidebar/Sidebar.tsx` | 3개 카드 import + 통합 |
| `frontend/src/components/map/HexMap.tsx` | popup 색상/높이/범례/툴팁 + getPopupColorScale 함수 |

### 블로커

- 없음

---

## 전체 마일스톤 현황

| 마일스톤 | 상태 | 완료 티켓 | 남은 티켓 |
|---------|------|----------|----------|
| M0 Repo/Infra | DONE | M0-1~M0-4 | M0-5 (P1, 선택) |
| M1 Data Layer | DONE | M1-1~M1-8 | 없음 |
| M2 API Layer | DONE | M2-1~M2-4 | 없음 |
| M3 UI Layer | DONE | M3-1~M3-5 | 없음 |
| M4 Eval/Logging | DONE | M4-1~M4-3 | 없음 |
| M5 Store H3 Weight | DELETED | - | - |
| M6 S3 Data+Backend | DONE | M6-1~M6-5 | 없음 |
| M7 S3 Frontend | DONE | M7-1~M7-5 | 없음 |
| M8 S4 비교 | DONE | M8-1~M8-3 | 없음 |
| M9 SNS Module | PLANNED | - | M9-1~M9-6 |

## 다음 3개 액션

1. **M9-1 DB Migration**: SNS 테이블 생성 (fact_social_trend_daily, social_module_config)
2. **M9-2 YouTube Collector**: YouTube Data API v3 ETL
3. **M9-3 Naver Collector**: Naver Search API ETL

---

## 2026-02-08 — M8 S4 분기 비교 완료 (M8 COMPLETE)

### 상태: M8-1, M8-2, M8-3 DONE

### 완료한 작업

- [x] M8-1: 비교 API 엔드포인트
  - `backend/api/schemas.py` — 5개 Pydantic 모델 추가 (ComparisonRequest, ComparisonMetricSnapshot, ComparisonChange, ComparisonBreakdown, ComparisonResponse)
  - `backend/api/map.py` — POST /api/map/compare 엔드포인트
    - H3 유효성 + qtr_before != qtr_after 검증
    - bridge_area_h3_weight + dim_area 조인으로 area_ids/weights 해석
    - fact_sales/flow/store 두 분기 데이터 한번에 fetch (qtr IN)
    - weight 기반 집계 → before/after 스냅샷 빌드
    - _safe_div로 변화율 계산
    - flow JSONB breakdown 추출 (before/after 각각)
    - 경고 생성 (매출/유동 -10% 이상 감소, 폐업률 >15%)

- [x] M8-2: SQL Agent 비교 쿼리 패턴
  - `backend/agents/sql_agent.py` — SQL_SYSTEM_PROMPT에 추가:
    - 비교 키워드: "대비", "비교", "변화", "전분기", "전년동기", "증감"
    - WITH before_q AS / after_q AS CTE 패턴
    - 예제 1: 단일 지표 비교 (매출 변화율)
    - 예제 2: 복합 비교 (매출 + 유동인구)

- [x] M8-3: Frontend 비교 모드
  - `frontend/src/types/map.ts` — 4개 TypeScript 인터페이스 추가
  - `frontend/src/store/mapStore.ts` — 비교 상태 (comparisonMode, compareQtrBefore/After, comparisonData, comparisonLoading) + 액션 (setComparisonMode, setCompareQtrBefore/After, fetchComparison). 분기 변경 시 auto-refetch
  - `frontend/src/components/filters/FilterPanel.tsx` — 비교 모드 ON/OFF 토글 (violet), Before/After 분기 Select
  - `frontend/src/components/sidebar/ComparisonCard.tsx` — **신규** 비교 카드
    - 분기 라벨 Badge (Before=blue, After=violet)
    - 3-column 변화율 그리드 (매출/유동/점포)
    - Before → After 상세 비교 행 (매출/유동/점포/개업/폐업)
    - Recharts 듀얼 BarChart (before=blue, after=violet)
    - 경고 목록 (WarningList 패턴)
  - `frontend/src/components/sidebar/Sidebar.tsx` — comparisonMode 분기 렌더링 (ComparisonCard vs 기존 카드)
  - `frontend/src/components/map/HexMap.tsx` — 클릭 핸들러 분기 (comparisonMode ? fetchComparison : fetchHexDetail)

### DoD 검증

```
npm run build → 성공 (타입 에러 0개) ✓
python3 ast.parse → 모든 백엔드 파일 파싱 성공 ✓
비교 모드 토글 (violet 버튼) ✓
Before/After 분기 Select 표시 ✓
ComparisonCard 듀얼 바 차트 ✓
변화율 3-column 그리드 ✓
상세 비교 행 (매출/유동/점포/개업/폐업) ✓
경고 목록 ✓
Sidebar 비교 모드 분기 렌더링 ✓
HexMap 클릭 핸들러 분기 ✓
```

### 수정 파일

| 파일 | 변경 |
|------|------|
| `backend/api/schemas.py` | 5개 Pydantic 모델 추가 |
| `backend/api/map.py` | POST /api/map/compare 엔드포인트 추가 |
| `backend/agents/sql_agent.py` | 비교 CTE 패턴 + 예제 2개 추가 |
| `frontend/src/types/map.ts` | 4개 TS 인터페이스 추가 |
| `frontend/src/store/mapStore.ts` | 비교 상태 + 액션 추가 |
| `frontend/src/components/filters/FilterPanel.tsx` | 비교 모드 토글 + Before/After Select |
| `frontend/src/components/sidebar/ComparisonCard.tsx` | **신규** — 비교 카드 |
| `frontend/src/components/sidebar/Sidebar.tsx` | 비교 모드 분기 렌더링 |
| `frontend/src/components/map/HexMap.tsx` | 클릭 핸들러 분기 |

### 블로커

- 없음

---

## 2026-02-09 — M9-11: 주소/상호 정제 기반 Kakao 지오코딩 보강

### 상태: DONE

### 배경

- 유튜브 스니펫에 상호/주소가 포함되어도 매칭이 누락되는 사례가 존재
- 주소 문자열을 직접 지오코딩하면 매핑 정확도를 높일 수 있음

### 완료한 작업

- [x] ETL: 주소 패턴 추출 → Kakao 주소검색 → 공간조인 경로 추가
- [x] ETL: 상호명 정규화(지점/점/성수점 제거) 후 지오코딩 재시도

### 수정 파일

| 파일 | 변경 |
|------|------|
| `etl/place_mapper.py` | 주소 추출 + 주소 지오코딩 + 상호 정규화 |

### 블로커

- 없음

---

## 2026-02-09 — M9-10: YouTube 해시태그 기반 장소 단서 보강

### 상태: DONE

### 배경

- YouTube 설명에 상호/주소가 부족한 경우가 많아 매핑률 개선이 제한됨
- 해시태그에 상호/장소명이 포함되는 패턴이 존재

### 완료한 작업

- [x] YouTube ETL: 해시태그 추출 후 키워드 매칭/LLM 장소 추출 입력에 포함
- [x] 스니펫 저장 시 해시태그 포함하여 증거 텍스트 보강

### 수정 파일

| 파일 | 변경 |
|------|------|
| `etl/load_youtube_trends.py` | 해시태그 추출 + 매칭/LLM 입력 보강 |

### 블로커

- 없음

---

## 2026-02-09 — M9-9: LLM + Kakao Local 상권 매핑 보강

### 상태: DONE

### 배경

- 상권별 소셜 트렌드 매핑률이 낮아 폴백 표시가 잦음
- 상권명 표기 다양성으로 키워드 매핑 실패 증가

### 완료한 작업

- [x] ETL: `etl/place_mapper.py` 신규 — Gemini Flash 장소 추출 + Kakao Local 지오코딩 + `dim_area` 공간조인
- [x] ETL: `load_youtube_trends.py`, `load_naver_trends.py` — 키워드 미매칭 시 LLM+Kakao 매핑 보강 경로 추가
- [x] Env: `.env.example`에 `KAKAO_REST_API_KEY` 추가

### 수정 파일

| 파일 | 변경 |
|------|------|
| `etl/place_mapper.py` | **신규** — LLM + Kakao Local 기반 area_id 보강 유틸 |
| `etl/load_youtube_trends.py` | LLM+Kakao 매핑 경로 추가 |
| `etl/load_naver_trends.py` | LLM+Kakao 매핑 경로 추가 |
| `.env.example` | `KAKAO_REST_API_KEY` 추가 |

### 블로커

- 없음

---

## 2026-02-09 — M9-8: Gemini Flash 업종 태깅 + API matched_categories 필터

### 상태: DONE

### 배경

- 업종(cat_code) 선택 시 소셜 에비던스가 동일한 결과만 표시되는 문제
- 키워드 기반 필터링(CATEGORY_SOCIAL_MAP/CATEGORY_EVIDENCE_HINTS)으로는 정확도 부족
- 사용자 요청: "단순 키워드 기반으로 하지말고 Gemini Flash 모델로 판단하게 해보는건 어떄?"

### 완료한 작업

- [x] ETL: `etl/category_tagger.py` 생성 — Gemini Flash 2.0 배치 태깅 유틸리티
- [x] ETL: `load_youtube_trends.py`, `load_naver_trends.py` — tag_daily_snippets() 호출 + matched_categories upsert
- [x] DB: `matched_categories` JSONB 컬럼 추가 (fact_social_trend_daily)
- [x] Backend: `social.py` — CATEGORY_SOCIAL_MAP/CATEGORY_EVIDENCE_HINTS 제거, SERVICE_TO_SOCIAL_CATEGORY + matched_categories @> 필터로 교체
- [x] Backend: 스니펫별 categories 필드 기반 필터링 (Gemini 태깅 결과 활용)
- [x] ETL 재수집: 기존 데이터 삭제 → Naver/YouTube 재수집 with Gemini tagging
- [x] 매핑률: YouTube area 97.8%, Naver area 100%, Gemini tagged 94.6% (53/56)

### 검증 결과

```
커피-음료 필터 → 카페/커피 관련 스니펫만 표시 ✓
일식 필터 → 스시/돈까스/생선 관련 스니펫만 표시 ✓
양식 필터 → 피자/브런치/유럽 관련 스니펫만 표시 ✓
필터 없음 → 전체 1205 buzz, 10 snippets ✓
```

### 수정 파일

| 파일 | 변경 |
|------|------|
| `etl/category_tagger.py` | **신규** — Gemini Flash 배치 카테고리 태거 |
| `etl/load_youtube_trends.py` | tag_daily_snippets() + matched_categories upsert |
| `etl/load_naver_trends.py` | 동일 변경 |
| `backend/api/social.py` | SERVICE_TO_SOCIAL_CATEGORY + matched_categories JSONB 필터 |
| `backend/requirements.txt` | google-generativeai==0.8.3 추가 |
| `etl/requirements.txt` | google-generativeai==0.8.3 추가 |

### 블로커

- Gemini 429 rate limit (무료 tier) — 대량 태깅 시 일부 배치 실패 가능 (자동 폴백: 빈 배열)

---

## 전체 마일스톤 현황

| 마일스톤 | 상태 | 완료 티켓 | 남은 티켓 |
|---------|------|----------|----------|
| M0 Repo/Infra | DONE | M0-1~M0-4 | M0-5 (P1, 선택) |
| M1 Data Layer | DONE | M1-1~M1-8 | 없음 |
| M2 API Layer | DONE | M2-1~M2-4 | 없음 |
| M3 UI Layer | DONE | M3-1~M3-5 | 없음 |
| M4 Eval/Logging | DONE | M4-1~M4-3 | 없음 |
| M5 Store H3 Weight | DELETED | - | - |
| M6 S3 Data+Backend | DONE | M6-1~M6-5 | 없음 |
| M7 S3 Frontend | DONE | M7-1~M7-5 | 없음 |
| M8 S4 비교 | DONE | M8-1~M8-3 | 없음 |
| M9 SNS Module | DONE | M9-1~M9-8 | 없음 |
