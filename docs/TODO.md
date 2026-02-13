# K-CIA Lite — 실행용 작업 티켓 (TODO.md)

**작성일:** 2026-01-30
**최종 업데이트:** 2026-02-13
**전략:** 시나리오 1 우선, M0~M11 완료 (Phase 2 완료)

---

## M0: Repo/Infra 준비

### M0-1: 모노레포 디렉토리 구조 확정 및 생성 [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 프로젝트 표준 구조를 확립하여 이후 모든 티켓의 파일 위치를 확정 |
| **작업** | `frontend/`, `backend/`, `etl/`, `tests/`, `docs/` 디렉토리 생성. 각 디렉토리에 최소 스켈레톤 파일 배치 |
| **산출물** | 디렉토리 트리, 각 디렉토리의 `__init__.py` 또는 `package.json` |
| **의존성** | 없음 |
| **리스크** | 낮음 |
| **DoD** | `tree` 명령으로 구조 확인, 문서와 일치 |

### M0-2: docker-compose.yml 작성 [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 로컬 개발 환경 일원화 (Postgres + FastAPI + Next.js) |
| **작업** | Postgres(PostGIS+h3-pg 확장), FastAPI dev, Next.js dev 서비스 정의. `.env.example` 작성 |
| **산출물** | `docker-compose.yml`, `.env.example` |
| **의존성** | M0-1 |
| **리스크** | h3-pg 확장이 공식 Postgres 이미지에 없을 수 있음 → 커스텀 Dockerfile 또는 Python h3 라이브러리로 대체 |
| **DoD** | `docker-compose up` → 3개 서비스 기동, health check 통과 |

### M0-3: Next.js 14 프로젝트 초기화 [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 프론트엔드 스켈레톤 생성 |
| **작업** | `npx create-next-app@14` (App Router, TypeScript, TailwindCSS). shadcn/ui 초기 설정. Deck.gl + react-map-gl 의존성 추가 |
| **산출물** | `frontend/` 내 Next.js 프로젝트 |
| **의존성** | M0-1 |
| **리스크** | 낮음 |
| **DoD** | `npm run dev` → 기본 페이지 렌더링 |

### M0-4: FastAPI 프로젝트 스켈레톤 [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 백엔드 스켈레톤 생성 |
| **작업** | `backend/main.py` (FastAPI app + `/health` endpoint), `requirements.txt`, `Dockerfile` |
| **산출물** | `backend/` 내 FastAPI 프로젝트 |
| **의존성** | M0-1 |
| **리스크** | 낮음 |
| **DoD** | `curl localhost:8000/health` → 200 OK |

### M0-5: DB 마이그레이션 도구 및 CI 설정 [P1]

| 항목 | 내용 |
|------|------|
| **목적** | 스키마 변경 추적 + 코드 품질 자동 검사 |
| **작업** | Alembic 설정 (또는 Supabase migrations). ruff(Python) + eslint+prettier(JS) 설정 |
| **산출물** | `alembic.ini`, lint config 파일들 |
| **의존성** | M0-2, M0-3, M0-4 |
| **리스크** | 낮음 |
| **DoD** | `alembic upgrade head` 성공, `ruff check` + `eslint` 통과 |

---

## M1: Data Layer (시나리오 1 최소 데이터셋)

### M1-1: DDL 실행 (핵심 테이블 생성) [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 시나리오 1에 필요한 모든 테이블 생성 |
| **작업** | `dim_area`, `dim_category`, `bridge_area_h3_weight`, `fact_sales_area_qtr`, `fact_flow_area_qtr`, `fact_store_area_qtr`, `preset_area_scope`, `analysis_run`, 수집 메타 테이블(`ingest_runs`, `raw_objects`, `schema_registry`) 생성 |
| **산출물** | 마이그레이션 SQL 파일 |
| **의존성** | M0-2 (DB 기동) |
| **리스크** | PostGIS 확장 활성화 필요 (`CREATE EXTENSION postgis`) |
| **DoD** | 모든 테이블 `\dt`로 확인, PostGIS/pgvector 확장 활성 |

### M1-2: D9(행정동 SHP) + D3(상권영역) 적재 → dim_area [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 공간 기준 테이블 구축 (행정동 4개 + 상권 20~40개) |
| **작업** | D9 SHP 다운로드 → 성수동 4개 동 필터 → EPSG:4326 변환 → `dim_area(ADMIN_DONG)` 적재. D3 CSV/SHP 다운로드 → EPSG:5181→4326 변환 → 성수동 상권 필터 → `dim_area(COMMERCIAL_AREA)` 적재. `preset_area_scope` 프리셋 적재 |
| **산출물** | `etl/collectors/boundary_collector.py`, 적재된 dim_area 행 |
| **의존성** | M1-1 |
| **리스크** | D3 폴리곤 미제공 시 centroid+면적 근사 → A2 가정 |
| **DoD** | `SELECT count(*) FROM dim_area WHERE area_type='ADMIN_DONG'` = 4, `COMMERCIAL_AREA` ≥ 10 |

### M1-3: H3 polyfill (res=10) → bridge_area_h3_weight [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 폴리곤→H3 매핑으로 모든 fact 데이터를 Hex 단위로 집계 가능하게 함 |
| **작업** | dim_area 폴리곤을 h3 라이브러리로 polyfill(res=10). 교차면적 비율로 weight 산출. `bridge_area_h3_weight` 적재 |
| **산출물** | `etl/processors/h3_mapper.py`, 적재된 bridge 행 |
| **의존성** | M1-2 |
| **리스크** | 작은 상권이 res=10에서도 Hex 0개일 수 있음 → centroid로 가장 가까운 Hex 1개 할당 |
| **DoD** | `SELECT count(DISTINCT h3_index) FROM bridge_area_h3_weight` > 50 |

### M1-4: D1(매출) ETL → fact_sales_area_qtr [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 매출 데이터 적재 (시나리오 1 핵심) |
| **작업** | ZIP 다운로드 → CSV 파싱 → 성수동 상권코드 필터 → 최근 8분기 → `fact_sales_area_qtr` upsert. `dim_category` 업종 매핑 동시 적재. raw 파일 보관 |
| **산출물** | `etl/collectors/seoul_zip_collector.py`, `etl/processors/sales_processor.py`, `etl/load_sales.py` (ZIP), `etl/load_sales_api.py` (API) |
| **의존성** | M1-1, M1-2 |
| **리스크** | CSV 인코딩(cp949/utf-8-sig) 불일치 → 자동 감지 로직 |
| **DoD** | `SELECT count(*) FROM fact_sales_area_qtr` = 4,681 rows (13분기: 2022Q1~2025Q1) ✓ |

### M1-5: D5(유동) ETL → fact_flow_area_qtr [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 유동인구 데이터 적재 (Hex 높이, 시간대/요일 분석) |
| **작업** | API 호출 → 성수동 상권코드 필터 → 시간대/요일/성별/연령 breakdown을 JSONB로 저장 → `fact_flow_area_qtr` upsert |
| **산출물** | `etl/load_flow_api.py` |
| **의존성** | M1-1, M1-2 |
| **리스크** | 파일 용량 클 수 있음(전국 데이터) → 스트리밍 파싱 |
| **DoD** | `SELECT count(*) FROM fact_flow_area_qtr` = 92 rows (4분기) ✓, JSONB breakdown 필드 검증 ✓ |

### M1-6: D2(점포) ETL → fact_store_area_qtr [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 경쟁/개폐업 데이터 적재 |
| **작업** | API 호출 → 성수동 행정동코드 필터 → `fact_store_area_qtr` upsert |
| **산출물** | `etl/load_store_api.py`, `etl/collectors/seoul_api_collector.py` |
| **의존성** | M1-1, M1-2 |
| **리스크** | API 서비스명 오류(`VwsmStorCdTrdarAdong` → `VwsmAdstrdStorW`), 행정동코드 체계 불일치(DB `1104xxxx` vs API `1120xxxx`) — 모두 해결 완료 |
| **DoD** | `SELECT count(*) FROM fact_store_area_qtr` = 1,459 rows (4분기: 2024Q2~2025Q1) ✓ |

### M1-7: 품질 체크 + dim_category 검증 [P1] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 적재 데이터 신뢰성 확보 |
| **작업** | 분기별 coverage 리포트, 결측율, PK 중복 검증, QoQ 이상치 검출 스크립트 |
| **산출물** | `etl/quality/check_quality.py`, 리포트 출력 |
| **의존성** | M1-4, M1-5, M1-6 |
| **리스크** | 낮음 |
| **DoD** | 품질 리포트 26/26 통과 ✓ |

### M1-8: (Should) D11 실시간 스냅샷 적재기 [P1] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 후행성 보정용 실시간 데이터 수집 시작 |
| **작업** | `fact_realtime_congestion_area` 테이블 생성. 성수동 관련 장소 매핑 확인. 장소별 스냅샷 수집 스크립트 |
| **산출물** | `etl/load_realtime_api.py`, `etl/collectors/seoul_api_collector.py` |
| **의존성** | M1-1 |
| **리스크** | 성수동 장소가 120개 목록에 없을 수 있음 (A2 가정) |
| **DoD** | 성수카페거리, 뚝섬역 스냅샷 적재 확인 ✓ |

---

## M2: API Layer (analytics + chat 최소)

### M2-1: Map API 엔드포인트 [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 프론트엔드 맵 렌더링에 필요한 데이터 제공 |
| **작업** | `GET /api/map/hexagons?area_type=&category=&qtr=` (H3 그리드 + 유동/매출/점포 집계), `GET /api/map/hexagon/{h3_index}` (상세 6개 카드) |
| **산출물** | `backend/api/map.py` |
| **의존성** | M1 완료 |
| **리스크** | H3 집계 쿼리 성능 → 필요 시 materialized view |
| **DoD** | curl로 hexagons 조회 → GeoJSON 형태 응답, area_type 토글 동작 |

### M2-2: Data API 엔드포인트 [P0] ✅ DONE (2026-01-31)

| 항목 | 내용 |
|------|------|
| **목적** | 필터/토글에 필요한 메타데이터 제공 |
| **작업** | `GET /api/data/categories`, `GET /api/data/area-scope` |
| **산출물** | `backend/api/data.py` |
| **의존성** | M1 완료 |
| **리스크** | 낮음 |
| **DoD** | curl로 업종 목록, 영역 프리셋 조회 성공 |

### M2-3: LangGraph 에이전트 구현 (Supervisor + SQL + Insight) [P0] ✅ DONE (2026-02-01)

| 항목 | 내용 |
|------|------|
| **목적** | 챗봇 핵심 로직 — 자연어 질의 → 데이터 근거 응답 |
| **작업** | Supervisor(라우터), SQL Agent(자연어→SQL, 안전규칙), Insight Agent(결과→근거/리스크/추천 구조화). LangGraph 그래프 정의 |
| **산출물** | `backend/agents/supervisor.py`, `backend/agents/sql_agent.py`, `backend/agents/insight_agent.py`, `backend/agents/graph.py` |
| **의존성** | M1 완료, OPENAI_API_KEY |
| **리스크** | SQL Agent 정확도 — 골든 쿼리로 검증(M4), 모델 선택(4o-mini → 4o 에스컬레이션) |
| **DoD** | "디저트 카페 Top3 추천" 질의 → SQL 생성 → 실행 → 근거 기반 응답 반환 |

### M2-4: Chat API 엔드포인트 [P0] ✅ DONE (2026-02-01)

| 항목 | 내용 |
|------|------|
| **목적** | 프론트엔드 챗봇과 연동 |
| **작업** | `POST /api/chat` (스트리밍 응답 지원, `data_asof` 포함) |
| **산출물** | `backend/api/chat.py` |
| **의존성** | M2-3 |
| **리스크** | 스트리밍 응답 형식(SSE vs WebSocket) — SSE로 시작 |
| **DoD** | curl로 챗 질의 → 스트리밍 응답 수신, data_asof 필드 포함 |

---

## M3: UI Layer (3D Hex + 사이드바 + 챗)

### M3-1: Deck.gl 3D Hex 맵 구현 [P0] ✅ DONE (2026-02-01)

| 항목 | 내용 |
|------|------|
| **목적** | 핵심 시각화 — 3D 헥사곤 맵 |
| **작업** | Deck.gl ColumnLayer(H3), elevation=유동/매출, color=매출증감(QoQ). react-map-gl 기본 맵 타일 |
| **산출물** | `frontend/src/components/map/HexMap.tsx` |
| **의존성** | M2-1 |
| **리스크** | Deck.gl 초기 로딩 → 데이터 경량화, 레이지 로딩 |
| **DoD** | 브라우저에서 3D 맵 렌더링 < 3초 |

### M3-1a: 지도 타일 폴백 스타일 [P1] ✅ DONE (2026-02-08)

| 항목 | 내용 |
|------|------|
| **목적** | Mapbox 토큰 미설정 시에도 맵 타일 렌더링 보장 |
| **작업** | Mapbox 스타일 대신 CARTO 스타일로 폴백 적용 |
| **산출물** | 폴백 mapStyle 로직 |
| **의존성** | M3-1 |
| **리스크** | 낮음 |
| **DoD** | 토큰 없이도 지도 타일 표시됨 |

### M3-2: 필터 패널 + 영역 토글 [P0] ✅ DONE (2026-02-02)

| 항목 | 내용 |
|------|------|
| **목적** | 업종/분기/영역 기준 필터링 |
| **작업** | 좌측 패널: 업종 셀렉트, 분기 셀렉트, 행정동/상권 토글. Zustand 상태 관리 |
| **산출물** | `frontend/src/components/filters/FilterPanel.tsx`, `frontend/src/store/` |
| **의존성** | M2-2 |
| **리스크** | 낮음 |
| **DoD** | 토글 전환 시 맵 데이터 갱신 |

### M3-2a: 지도 목업 데이터 제거 + Mapbox 토큰 보강 [P1] ✅ DONE (2026-02-02)

| 항목 | 내용 |
|------|------|
| **목적** | 목업 라벨/핫스팟 제거 및 지도 로딩 안정화 |
| **작업** | 하드코딩 상권/핫스팟 제거, AREA_LABELS 삭제, API fallback 정리, NEXT_PUBLIC_MAPBOX_TOKEN 추가 |
| **산출물** | `frontend/src/components/map/HexMap.tsx`, `.env` |
| **의존성** | M3-1 |
| **리스크** | 낮음 |
| **DoD** | 지도에 목업 라벨 미표시, Mapbox 타일 정상 로딩 |

### M3-3: Hex 클릭 → 사이드바 카드 [P0] ✅ DONE (2026-02-03)

| 항목 | 내용 |
|------|------|
| **목적** | 선택 구역 상세 정보 표시 |
| **작업** | Hex 클릭 이벤트 → `/api/map/hexagon/{h3}` 호출 → 사이드바에 카드 5개(유동/매출/경쟁/성장/리스크) + as-of 배지 |
| **산출물** | `frontend/src/components/sidebar/Sidebar.tsx`, `frontend/src/components/sidebar/MetricCard.tsx` |
| **의존성** | M2-1, M3-1 |
| **리스크** | 낮음 |
| **DoD** | Hex 클릭 → 사이드바 열림, 5개 카드 데이터 표시 ✓ |

### M3-4: 챗봇 UI (스트리밍) [P0] ✅ DONE (2026-02-03)

| 항목 | 내용 |
|------|------|
| **목적** | AI 챗봇 인터페이스 |
| **작업** | Vercel AI SDK 기반 챗 패널. 스트리밍 응답 렌더링. 구조화 응답(근거카드/리스크/추천/체크리스트) 커스텀 렌더링 |
| **산출물** | `frontend/src/components/chat/ChatPanel.tsx` |
| **의존성** | M2-4 |
| **리스크** | Vercel AI SDK와 FastAPI SSE 호환 확인 필요 |
| **DoD** | 챗봇 질의 → 스트리밍 응답 표시, 구조화 카드 렌더링 ✓ |

### M3-5: as-of 배지 + 후행성 경고 컴포넌트 [P1] ✅ DONE (2026-02-03)

| 항목 | 내용 |
|------|------|
| **목적** | 데이터 후행성 UX 반영 |
| **작업** | `AsOfBadge` 컴포넌트 (분기/월/실시간 구분 색상), 후행성 경고 배너, (Should) D11 실시간 확인 버튼 |
| **산출물** | `frontend/src/components/common/AsOfBadge.tsx` |
| **의존성** | M3-3 |
| **리스크** | 낮음 |
| **DoD** | 모든 카드에 as-of 배지 표시 ✓ |

### M3-6: 선택 상권 카드 컨텍스트 → 챗봇 전달 [P1] ✅ DONE (2026-02-03)

| 항목 | 내용 |
|------|------|
| **목적** | 챗봇이 현재 선택된 상권 카드 정보를 기본 컨텍스트로 활용 |
| **작업** | `/api/map/hexagon/{h3}` 응답을 `/api/chat` 요청에 포함, Insight Agent 입력에 주입 |
| **산출물** | `frontend/src/hooks/useStreamingChat.ts`, `backend/api/chat.py`, `backend/agents/insight_agent.py` |
| **의존성** | M3-3, M2-4 |
| **리스크** | 요청 페이로드 크기 증가 → 필요 시 요약 필드만 전송 |
| **DoD** | 선택 상권 질문 시 카드 데이터 기반 응답 확인 |

---

## M4: Eval/Logging

### M4-1: 골든 쿼리 정의 및 회귀 테스트 [P0] ✅ DONE (2026-02-03)

| 항목 | 내용 |
|------|------|
| **목적** | SQL Agent 품질 보증 |
| **작업** | 골든 쿼리 3종 정의(TopN 추천 / QoQ 비교 / 적합도 점수). 입력→SQL→결과 비교 스크립트. **추가**: sql_result 미반환 버그 수정, 업종명 fuzzy 매칭, Insight 환각 방지 |
| **산출물** | `tests/golden_queries/golden_queries.json`, `tests/test_sql_agent.py` |
| **의존성** | M2-3 |
| **리스크** | 낮음 |
| **DoD** | Validation 3/3 통과 ✓, Integration 3/3 통과 ✓ |

### M4-2: analysis_run 저장 로직 [P1] ✅ DONE (2026-02-03)

| 항목 | 내용 |
|------|------|
| **목적** | 사용자 분석 결과 재현/감사 |
| **작업** | 챗봇 응답 시 `analysis_run` 테이블에 질문/필터/SQL/결과/가정/asof 자동 저장 |
| **산출물** | `backend/services/analysis_logger.py` |
| **의존성** | M2-4 |
| **리스크** | 낮음 |
| **DoD** | 챗봇 질의 후 `analysis_run` 행 생성 확인 |

### M4-3: 이벤트 로그 [P2] ✅ DONE (2026-02-03)

| 항목 | 내용 |
|------|------|
| **목적** | 사용자 행동 추적 (KPI 측정) |
| **작업** | 이벤트 로그 테이블 생성. 클라이언트 이벤트 전송 (`HEX_CLICK`, `ASK`, `FILTER_APPLY`) |
| **산출물** | `backend/api/events.py`, `frontend/src/lib/analytics.ts` |
| **의존성** | M3 완료 |
| **리스크** | 낮음 |
| **DoD** | 이벤트 1건 이상 기록 확인 |

---

## ~~M5: 점포 수 기반 H3 Weight~~ — 삭제됨 (2026-02-07)

> 불필요로 판단하여 삭제. 면적 기반 weight만 사용.

---

## M6: S3 Data + Backend (D8 ETL + 인구통계 필터)

### M6-1: DB Migration (fact_facility_area_qtr) [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | D8 집객시설 데이터 저장 테이블 생성 |
| **작업** | `backend/migrations/004_s3_facility.sql` 작성 (fact_facility_area_qtr) |
| **산출물** | Migration SQL |
| **의존성** | M1-1 |
| **리스크** | 낮음 |
| **DoD** | 테이블 생성, PK/FK 정상 ✓ |

### M6-2: D8 ETL (집객시설) [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | 집객시설 데이터 수집 및 적재 |
| **작업** | `etl/load_facility_api.py` — Seoul API `VwsmTrdarFcltyQq` (OA-15580) → fact_facility_area_qtr. seoul_api_collector에 D8_FACILITY 서비스 추가. 원래 계획(VwsmTrdarHitterIndQq/OA-15581)은 API 접근 불가로 대체 (DEC-018) |
| **산출물** | ETL 스크립트, 적재 데이터 (6,800행, 20분기, 17상권, 20시설유형) |
| **의존성** | M6-1 |
| **리스크** | API가 분기 파라미터 무시 → 전체 1회 fetch로 해결 |
| **DoD** | fact_facility_area_qtr 6,800행 ✓, 2025Q1~Q3 포함 ✓, 시설 유형 20종 ✓ |

### M6-3: Hexagons API 인구통계 필터 [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | 팝업 모드에서 타겟 인구 기반 필터링 |
| **작업** | `backend/api/map.py` — target_gender, target_age, mode 파라미터 추가. popup mode SQL (flow_by_demo JSONB 추출) |
| **산출물** | 확장된 hexagons API |
| **의존성** | M2-1 |
| **리스크** | JSONB 쿼리 성능 |
| **DoD** | popup mode API 호출 시 target_flow, target_flow_ratio 반환 ✓ (이미 기존 코드에 구현됨) |

### M6-4: Hexagon Detail 확장 (시설 + 인구통계 카드) [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | Hex 상세에 시설/인구통계/시간대 추천 카드 추가 |
| **작업** | `backend/api/schemas.py` — FacilityCard, DemoCard, TimeSlotRecommendation. `backend/api/map.py` — hexagon detail에 추가 필드 |
| **산출물** | 확장된 hexagon detail API |
| **의존성** | M6-1, M6-2 |
| **리스크** | 낮음 |
| **DoD** | hexagon detail 응답에 facility, demo, time_slot 필드 포함 ✓ |

### M6-5: SQL Agent 프롬프트 업데이트 [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | SQL Agent가 인구통계/시설 질의 처리 가능 |
| **작업** | `backend/agents/sql_agent.py` — flow_by_demo JSONB 패턴, fact_facility_area_qtr 스키마, ALLOWED_TABLES 추가 |
| **산출물** | 업데이트된 SQL Agent |
| **의존성** | M6-1 |
| **리스크** | 낮음 |
| **DoD** | "20대 여성 유동인구 Top3" 질의에 JSONB 추출 SQL 생성 ✓ |

---

## M7: S3 Frontend (팝업 모드 UI)

### M7-1: Zustand Store 확장 [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | 팝업 모드 상태 관리 |
| **작업** | `frontend/src/store/mapStore.ts` — mode, targetGender, targetAge, setMode, setTargetGender, setTargetAge |
| **산출물** | 확장된 Zustand store |
| **의존성** | M3-2 |
| **리스크** | 낮음 |
| **DoD** | 팝업 모드 상태 전환 동작 |

### M7-2: TypeScript 타입 추가 [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | 새 인터페이스 타입 안전성 |
| **작업** | `frontend/src/types/map.ts` — FacilityCard, DemoCard, TimeSlotRecommendation, HexagonSummary/DetailResponse 확장 |
| **산출물** | TypeScript 타입 |
| **의존성** | 없음 |
| **리스크** | 낮음 |
| **DoD** | npm run build 타입 에러 없음 |

### M7-3: 팝업 모드 필터 UI [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | 팝업 모드 전환 + 타겟 필터 선택 |
| **작업** | `frontend/src/components/filters/PopupModePanel.tsx` — Default/Popup 토글, 성별 선택, 연령대 선택. FilterPanel.tsx에 통합 |
| **산출물** | PopupModePanel 컴포넌트 |
| **의존성** | M7-1 |
| **리스크** | 낮음 |
| **DoD** | 팝업 모드 토글 동작, 필터 파라미터 API 전달 |

### M7-4: 사이드바 카드 추가 (3개) [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | 팝업 모드 상세 정보 |
| **작업** | FacilityCard.tsx, DemoCard.tsx, TimeSlotCard.tsx. Sidebar.tsx에 조건부 렌더링 (데이터 있으면 표시) |
| **산출물** | 사이드바 카드 3개 |
| **의존성** | M6-4, M7-1 |
| **리스크** | 낮음 |
| **DoD** | 사이드바에 3개 카드 표시 (시설/인구통계/시간대) ✓ |

### M7-4a: 인구통계 막대 가독성 보정 [P1] ✅ DONE (2026-02-08)

| 항목 | 내용 |
|------|------|
| **목적** | 인구통계 막대 그래프 가독성 개선 |
| **작업** | 막대 채움/배경 대비 강화, 최소 높이 보장 |
| **산출물** | DemoCard 막대 스타일 보정 |
| **의존성** | M7-4 |
| **리스크** | 낮음 |
| **DoD** | 라이트/다크 모드에서 막대가 명확히 보임 |

### M7-5: HexMap 팝업 모드 시각화 [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | 팝업 모드 시각 구분 |
| **작업** | `frontend/src/components/map/HexMap.tsx` — popup mode: elevation=target_flow, color=target_flow_ratio (파랑→보라), 범례 전환, 툴팁 타겟 유동인구 표시 |
| **산출물** | 확장된 HexMap |
| **의존성** | M7-1, M6-3 |
| **리스크** | 낮음 |
| **DoD** | popup 모드에서 색상/높이/범례/툴팁 변경 확인 ✓ |

---

## M8: S4 분기 비교

### M8-1: 비교 API [P0] ✅ DONE (2026-02-08)

| 항목 | 내용 |
|------|------|
| **목적** | 2개 분기 지표 비교 |
| **작업** | `backend/api/map.py` — POST /api/map/compare. `backend/api/schemas.py` — ComparisonRequest, ComparisonMetricSnapshot, ComparisonChange, ComparisonBreakdown, ComparisonResponse |
| **산출물** | 비교 API 엔드포인트 |
| **의존성** | M2-1 |
| **리스크** | 낮음 |
| **DoD** | 2개 분기 비교 API 호출 시 before/after snapshots + change rates 반환 ✓ |

### M8-2: SQL Agent 비교 쿼리 패턴 [P0] ✅ DONE (2026-02-08)

| 항목 | 내용 |
|------|------|
| **목적** | 분기 비교 자연어 질의 처리 |
| **작업** | `backend/agents/sql_agent.py` — 분기 비교 SQL 패턴 (WITH before_q AS, after_q AS CTE) + 비교 키워드 목록 |
| **산출물** | 업데이트된 SQL Agent |
| **의존성** | M6-5 |
| **리스크** | 낮음 |
| **DoD** | "2024Q3 대비 Q4 매출 변화" 질의에 비교 CTE SQL 생성 ✓ |

### M8-3: Frontend 비교 모드 [P0] ✅ DONE (2026-02-08)

| 항목 | 내용 |
|------|------|
| **목적** | 비교 모드 UI |
| **작업** | Zustand: comparisonMode, compareQtrBefore/After, comparisonData, fetchComparison. FilterPanel 비교 모드 토글 + Before/After Select. ComparisonCard.tsx (듀얼 바 차트, 변화율 그리드, 상세 비교 행, 경고). Sidebar 조건부 렌더링. HexMap 클릭 핸들러 분기 |
| **산출물** | 비교 UI 컴포넌트 |
| **의존성** | M8-1 |
| **리스크** | 낮음 |
| **DoD** | 비교 모드에서 Before/After 카드 + 차트 렌더링 ✓ |

### M8-3a: 비교 업종 스코프 토글 [P1] ✅ DONE (2026-02-08)

| 항목 | 내용 |
|------|------|
| **목적** | 비교 모드에서 업종 기준(전체/선택) 전환 |
| **작업** | `compareCategoryMode` 상태 추가, 업종 변경 시 비교 재조회, FilterPanel 토글 UI 추가 |
| **산출물** | 업종 스코프 토글 UI + 비교 API 요청 반영 |
| **의존성** | M8-3 |
| **리스크** | 낮음 |
| **DoD** | 업종 선택/토글에 따라 비교 변화율이 변경됨 |

---

## M9: SNS Module (YouTube + Naver)

### M9-1: DB Migration (SNS 테이블) [P0] ✅ DONE (2026-02-09)

| 항목 | 내용 |
|------|------|
| **목적** | SNS 데이터 저장 구조 |
| **작업** | `backend/migrations/005_sns_module.sql` — fact_social_trend_daily, social_module_config |
| **산출물** | Migration SQL |
| **의존성** | M1-1 |
| **리스크** | 낮음 |
| **DoD** | 테이블 생성 ✓, social_module_config 기본값(enabled=false) ✓, DEC-017 area_scope 반영 ✓ |

### M9-2: YouTube Collector + Loader [P0] ✅ DONE (2026-02-09)

| 항목 | 내용 |
|------|------|
| **목적** | YouTube 트렌드 데이터 수집 |
| **작업** | `etl/collectors/youtube_collector.py`, `etl/load_youtube_trends.py` — YouTube Data API v3, 키워드 검색, 일별 버즈/감성 |
| **산출물** | YouTube ETL |
| **의존성** | M9-1, YOUTUBE_API_KEY |
| **리스크** | 무료 할당량 (10K units/day) |
| **DoD** | Collector: search.list 페이징+quota 에러 처리 ✓, Loader: 일별 집계+감성분석+best-effort 상권매핑+upsert ✓ |

### M9-3: Naver Collector + Loader [P0] ✅ DONE (2026-02-09)

| 항목 | 내용 |
|------|------|
| **목적** | Naver Blog/Cafe 트렌드 수집 |
| **작업** | `etl/collectors/naver_collector.py`, `etl/load_naver_trends.py` — Naver Search API, 키워드 검색 |
| **산출물** | Naver ETL |
| **의존성** | M9-1, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET |
| **리스크** | 낮음 (25K calls/day) |
| **DoD** | Collector: Blog+Cafe 검색+페이징+rate limit 에러 처리 ✓, Loader: 일별 집계+감성분석+best-effort 상권매핑+upsert ✓ |

### M9-4: Social Agent (LangGraph) [P0] ✅ DONE (2026-02-09)

| 항목 | 내용 |
|------|------|
| **목적** | SNS 데이터 분석 에이전트 |
| **작업** | `backend/agents/social_agent.py` — 모듈 ON/OFF 분기, 트렌드 요약/감성/키워드. `backend/agents/graph.py` — Social Agent 노드 추가. `backend/agents/insight_agent.py` — social_result 통합 |
| **산출물** | Social Agent |
| **의존성** | M9-1, M2-3 |
| **리스크** | 모듈 OFF 회귀 테스트 |
| **DoD** | social_agent_node 구현 ✓, graph.py 라우팅 (supervisor→sql→social→insight) ✓, insight_agent social_result 주입 ✓, OFF 시 social_result=None 처리 ✓ |

### M9-5: Social API Endpoint [P0] ✅ DONE (2026-02-09)

| 항목 | 내용 |
|------|------|
| **목적** | SNS 데이터 API |
| **작업** | `backend/api/social.py` — GET /api/social/trends, GET /api/social/config |
| **산출물** | Social API 엔드포인트 |
| **의존성** | M9-1 |
| **리스크** | 낮음 |
| **DoD** | /api/social/config 응답 ✓, /api/social/trends 데이터 반환 ✓, main.py 라우터 등록 ✓ |

### M9-6: Frontend SNS UI [P0] ✅ DONE (2026-02-09)

| 항목 | 내용 |
|------|------|
| **목적** | SNS 데이터 시각화 |
| **작업** | Zustand: socialEnabled, socialData, fetchSocialConfig/fetchSocialTrends/toggleSocial. `frontend/src/types/social.ts`. SocialBuzzCard (버즈량/감성/소스별/키워드/에비던스/일별 추이). FilterPanel 소셜 토글 |
| **산출물** | SNS UI 컴포넌트 |
| **의존성** | M9-5 |
| **리스크** | 낮음 |
| **DoD** | FilterPanel 소셜 토글 ✓, SocialBuzzCard 렌더링 ✓, Sidebar 조건부 표시 ✓, fetchSocialConfig 초기 호출 ✓ |

### M9-7: Social Trends 상권/업종/H3 매핑 연동 [P1] ✅ DONE (2026-02-09)

| 항목 | 내용 |
|------|------|
| **목적** | 헥스 클릭/업종 선택 시 해당 상권의 소셜 트렌드만 필터링 + ETL 매핑률 개선 |
| **작업** | (1) Backend: `/api/social/trends`에 h3_index/area_id/cat_code 필터 + CATEGORY_SOCIAL_MAP + 폴백 로직. (2) ETL: get_area_mapping()에 real_name + 랜드마크 매핑 추가 (카페거리 중복 방지). (3) Frontend: fetchSocialTrends 파라미터화, fetchHexDetail/setCategory/toggleSocial에서 자동 재조회, 필터 컨텍스트 뱃지 UI, 소셜 로딩 스켈레톤 |
| **산출물** | 7개 파일 수정 (social.py, load_youtube_trends.py, load_naver_trends.py, mapStore.ts, social.ts, SocialBuzzCard.tsx, Sidebar.tsx) |
| **의존성** | M9-5, M9-6 |
| **리스크** | 매핑률 목표(30%+) 미달 시 대부분 폴백 표시 가능 |
| **DoD** | h3_index 필터 API 동작 ✓, cat_code 필터 API 동작 ✓, 폴백(is_fallback=true) 동작 ✓, 프론트 자동 재조회 ✓, 필터 뱃지 표시 ✓ |

### M9-8: LLM + Kakao Local 상권 매핑 보강 [P1] ✅ DONE (2026-02-09)

| 항목 | 내용 |
|------|------|
| **목적** | 키워드 매핑 실패 시 장소 추출 + 지오코딩으로 area_id 보강 |
| **작업** | `etl/place_mapper.py` 신규, `load_youtube_trends.py`/`load_naver_trends.py`에 LLM+Kakao 매핑 경로 추가, `.env.example`에 `KAKAO_REST_API_KEY` 추가 |
| **산출물** | LLM+지오코딩 기반 매핑 유틸리티 + ETL 연동 |
| **의존성** | GEMINI_API_KEY, KAKAO_REST_API_KEY |
| **리스크** | Kakao API 쿼터/속도, LLM 호출 비용 |
| **DoD** | 키워드 미매칭 케이스에서 area_id 보강 ✓, 비활성 시 기존 로직 유지 ✓ |

### M9-9: YouTube 해시태그 기반 상호/장소 단서 보강 [P1] ✅ DONE (2026-02-09)

| 항목 | 내용 |
|------|------|
| **목적** | YouTube 설명 부족 시 해시태그를 활용해 장소 단서 추가 |
| **작업** | `etl/load_youtube_trends.py`에서 해시태그 추출 후 매칭/LLM 입력에 포함 |
| **산출물** | 해시태그 보강 로직 |
| **의존성** | M9-8 |
| **리스크** | 해시태그 노이즈 증가 가능 |
| **DoD** | 해시태그 포함 매칭/LLM 입력 ✓ |

### M9-10: 주소/상호 정제 기반 Kakao 지오코딩 보강 [P1] ✅ DONE (2026-02-09)

| 항목 | 내용 |
|------|------|
| **목적** | 주소 문자열/지점 표기 정제를 통해 지오코딩 매핑률 개선 |
| **작업** | `etl/place_mapper.py`에 주소 추출 + Kakao 주소검색 + 상호명 정규화 추가 |
| **산출물** | 주소/상호 보강 로직 |
| **의존성** | M9-8 |
| **리스크** | 주소 파싱 노이즈 가능 |
| **DoD** | 주소/상호 정제 경로 동작 ✓ |

### M9-12: SNS ETL 공간 매핑 구조 개선 [P1] ✅ DONE (2026-02-10)

| 항목 | 내용 |
|------|------|
| **목적** | SNS ETL 매핑률 근본 개선 — videos.list 확장 + per-area 집계 + 좌표 기반 공간 매핑 |
| **작업** | (1) `youtube_collector.py` get_video_details() 메서드 추가, (2) `load_youtube_trends.py` 대규모 재작성 (enrich_videos + match_area_ids + aggregate_by_date_area + spatial-first), (3) `load_naver_trends.py` 완전 재작성 (동일 구조), (4) `place_mapper.py` resolve_area_ids_multi() 추가 |
| **산출물** | YouTube 10/17 상권 (61.3% area-mapped), Naver 15/17 상권 (90.7% area-mapped) |
| **의존성** | M9-8, M9-10 |
| **리스크** | Kakao API 쿼터, Gemini rate limit |
| **DoD** | videos.list enrichment ✓, per-(date, area_id) aggregation ✓, spatial-first mapping ✓, YouTube 10/17 ✓, Naver 15/17 ✓ |

---

## M10: S2 피크타임 운영전략

### M10-1: Hexagons API 시간대 모드 [P0] ✅ DONE (2026-02-11)

| 항목 | 내용 |
|------|------|
| **목적** | 지도에서 시간대별 유동 패턴을 시각화할 데이터 제공 |
| **작업** | `backend/api/map.py` — `GET /api/map/hexagons` 에 `mode=timeslot` 파라미터 추가. flow_by_hour JSONB에서 피크 시간대 비중, 평일/주말 유동 패턴 계산. HexagonSummary에 `peak_hour`, `peak_hour_ratio`, `weekday_ratio` 필드 추가. `_compute_timeslot_summary()` 헬퍼 함수. timeslot 모드 `data_asof`는 `flow_qtr` 기준으로 반환. ETL flow_by_hour 필드명 버그 수정 + 재적재 |
| **산출물** | 확장된 hexagons API |
| **의존성** | M2-1 |
| **리스크** | JSONB 집계 쿼리 성능 — 필요 시 materialized view |
| **DoD** | `mode=timeslot` 호출 시 peak_hour="17_21", peak_hour_ratio=0.1919, weekday_ratio=0.7195 반환 ✓, data_asof=flow_qtr ✓ |

### M10-2: Hexagon Detail 운영전략 카드 [P0] ✅ DONE (2026-02-11)

| 항목 | 내용 |
|------|------|
| **목적** | 선택 구역의 피크/오프피크 기반 운영 추천 |
| **작업** | `backend/api/schemas.py` — OperatingStrategyCard, TimeSlotStrategy, WeekdayPattern 모델. `backend/api/map.py` — _build_operating_strategy(), _build_weekday_pattern() 빌더. 피크 시간대 유동비중 기반 인력 배분율 계산, 권장 영업시간 산출, 평일/주말 패턴 분석. flow_by_hour/weekday/demo를 H3 가중 집계로 통일 |
| **산출물** | OperatingStrategyCard API 응답 |
| **의존성** | M2-1, M6-4 |
| **리스크** | 매출 시간대별 데이터 없음 (D1은 분기 총액만) — 유동 기반 추정으로 대체 |
| **DoD** | hexagon detail에 operating_strategy 필드 포함, 피크/오프피크 시간대 + 권장 인력 배분 반환 ✓ |

### M10-3: SQL Agent 시간대/요일 분석 패턴 [P0] ✅ DONE (2026-02-11)

| 항목 | 내용 |
|------|------|
| **목적** | 챗봇에서 시간대/요일 관련 질의 처리 |
| **작업** | `backend/agents/sql_agent.py` — JSONB 시간대 추출 쿼리 패턴 추가 (flow_by_hour->>'11_14', 평일/주말 합산). 키워드 매핑: "피크타임", "오후", "주말", "야간", "심야", "인력", "영업시간". 4개 예제: 특정 시간대 유동인구, 피크 시간대 찾기, 주말 vs 평일 비교, 시간대별 매출 기여 추정. 매출 시간대 추정 주의사항(유동 기반 추정) |
| **산출물** | 업데이트된 SQL Agent |
| **의존성** | M2-3 |
| **리스크** | 낮음 |
| **DoD** | "오후 3~5시 유동인구", "주말 vs 평일 비교" 질의에 JSONB 추출 SQL 생성 ✓ |

### M10-4: HexMap 시간대 모드 시각화 [P0] ✅ DONE (2026-02-12)

| 항목 | 내용 |
|------|------|
| **목적** | 지도에서 시간대별 유동 패턴 시각화 |
| **작업** | `frontend/src/components/map/HexMap.tsx` — `elevationMetric: "timeslot"` 추가. 색상=피크 시간대 유동 비중 (파랑→빨강), 높이=유동인구. `frontend/src/store/mapStore.ts` — ElevationMetric에 timeslot 추가. 범례/툴팁 업데이트 |
| **산출물** | HexMap 시간대 모드 |
| **의존성** | M10-1, M3-1 |
| **리스크** | 낮음 |
| **DoD** | 시간대 모드 토글 시 색상/높이/범례/툴팁 변경 ✓, API mode=timeslot 전달 ✓, 빌드 성공 ✓ |

### M10-5: TimeSlotCard 확장 [P0] ✅ DONE (2026-02-12)

| 항목 | 내용 |
|------|------|
| **목적** | 피크/오프피크 상세 분석 표시 |
| **작업** | `frontend/src/components/sidebar/TimeSlotCard.tsx` — 피크/오프피크 자동 분류 (OperatingStrategy 기반, peak_slots/off_peak_slots), 요일×시간대 유동 히트맵 (flow_by_hour × flow_by_weekday 비례 추정), 평일 vs 주말 유동 비교 (비율 바 + 일별 막대). Sidebar.tsx에서 flow/operating_strategy props 전달 |
| **산출물** | 확장된 TimeSlotCard (3개 섹션: 피크분류 + 히트맵 + 평일/주말) |
| **의존성** | M7-4, M10-2 |
| **리스크** | 낮음 |
| **DoD** | 히트맵 + 평일/주말 비교 표시 ✓, 피크/오프피크 자동 분류 ✓, 빌드 성공 ✓ |

**Bugfix (2026-02-12)**
- 히트맵 색상 정규화 방식 개선 (min-max) — 낮은/높은 시간대 대비 강화

### M10-6: OperatingStrategyCard 컴포넌트 [P0] ✅ DONE (2026-02-12)

| 항목 | 내용 |
|------|------|
| **목적** | 운영전략 시각화 및 가정값 입력 |
| **작업** | `frontend/src/components/sidebar/OperatingStrategyCard.tsx` — 신규. 권장 영업시간 타임라인, 인력 스케줄 시각화 (시간대별 바), 가정값 입력 UI (객단가/회전율/좌석수). Sidebar.tsx에 조건부 렌더링 추가 |
| **산출물** | OperatingStrategyCard 컴포넌트 |
| **의존성** | M10-2, M10-5 |
| **리스크** | 가정값 입력 UX 복잡도 |
| **DoD** | 권장 영업시간 타임라인 ✓, 인력 스케줄 바 ✓, 가정값 입력(객단가/회전율/좌석수) ✓, 변경 시 실시간 재계산 ✓, 빌드 성공 ✓ |

**Bugfix (2026-02-12)**
- 객단가 입력 마지막 0 표시 누락 → text 입력 + 문자열 state로 표시 보존

---

## M11: S5 경쟁과밀/폐업 리스크 진단

### M11-1: 리스크 스코어 알고리즘 [P0] ✅ DONE (2026-02-13)

| 항목 | 내용 |
|------|------|
| **목적** | 구역별 리스크를 0~100으로 정량화 |
| **작업** | `backend/api/map.py` — `_calc_risk_score()` 함수. `risk_score = w1*폐업QoQ + w2*점포증가율 + w3*매출QoQ(-) + w4*경쟁밀도`. 각 요소를 선형 정규화(threshold 기반) 후 가중합 → 0~100 매핑. `backend/api/schemas.py` — RiskCard에 `risk_score: float`, `risk_level: str` (High/Medium/Low), `decomposition: list[RiskDecompositionItem]` 추가 |
| **산출물** | 리스크 스코어 계산 로직 |
| **의존성** | M2-1 |
| **리스크** | 가중치 튜닝 필요 — 기본값 제공 후 사용자 피드백으로 조정 |
| **DoD** | hexagon detail에 risk_score(0~100) + risk_level + decomposition 포함 ✓ |

### M11-2: Hexagons API 리스크 모드 [P0] ✅ DONE (2026-02-13)

| 항목 | 내용 |
|------|------|
| **목적** | 지도에서 리스크 수준 시각화 |
| **작업** | `backend/api/map.py` — `GET /api/map/hexagons` 에 `mode=risk` 파라미터 추가. HexagonSummary에 `risk_score`, `risk_level` 필드 추가. prev_store_agg CTE로 점포 QoQ 계산. 폐업률, 점포 증가율, 매출 QoQ, 경쟁밀도를 조합하여 계산 |
| **산출물** | 확장된 hexagons API |
| **의존성** | M11-1, M2-1 |
| **리스크** | JSONB 쿼리 성능 |
| **DoD** | `mode=risk` 호출 시 217개 Hex에 risk_score(29.5~69.2) + risk_level(Low/Medium/High) 포함 응답 반환 ✓ |

### M11-3: 리스크 분해 + 대안 구역 API [P0] ✅ DONE (2026-02-13)

| 항목 | 내용 |
|------|------|
| **목적** | 리스크 원인 분석 + 대안 추천 |
| **작업** | `backend/api/map.py` — `_find_alternatives()` 함수: 동일 area_type+업종 내 전체 Hex 리스크 계산 → 현재 Hex 제외 → 리스크 낮은 순 상위 2곳 반환. `backend/api/schemas.py` — AlternativeArea 모델 (h3_index, area_name, risk_score, risk_level, flow_total, sales_amt, store_cnt, close_rate, sales_qoq). HexagonDetailResponse에 alternatives 필드 추가. 기존 RiskDecompositionItem.contribution으로 기여도(%) 계산 가능 |
| **산출물** | 리스크 분해 + 대안 API |
| **의존성** | M11-1 |
| **리스크** | 대안 추천 시 동일 업종 데이터 부족 가능 — 전체 업종 폴백 |
| **DoD** | hexagon detail에 risk decomposition(4요소 기여도%) + alternatives(2곳) 필드 포함 ✓ |

### M11-4: SQL Agent 리스크 분석 패턴 [P0] ✅ DONE (2026-02-13)

| 항목 | 내용 |
|------|------|
| **목적** | 챗봇에서 리스크/경쟁 관련 질의 처리 |
| **작업** | `backend/agents/sql_agent.py` — 리스크 관련 SQL 패턴 추가. 폐업률 추세 쿼리 (QoQ 폐업수/점포수), 경쟁 밀도 비교 (상권별 업종 점포수), 리스크 랭킹 (폐업률+매출감소 복합). 키워드: "리스크", "폐업", "경쟁", "과밀", "위험", "포화" |
| **산출물** | 업데이트된 SQL Agent |
| **의존성** | M2-3 |
| **리스크** | 낮음 |
| **DoD** | "이 구역 디저트 업종 리스크 높은 이유" 질의에 폐업/경쟁/매출 분석 SQL 생성 |

### M11-5: HexMap 리스크 모드 시각화 [P0] ✅ DONE (2026-02-13)

| 항목 | 내용 |
|------|------|
| **목적** | 지도에서 리스크 레이어 시각화 |
| **작업** | `frontend/src/components/map/HexMap.tsx` — `getRiskColorScale()` (초록→노랑→빨강), `elevationMetric: "risk"` (높이=매출, 색상=리스크), 리스크 전용 툴팁 (스코어/레벨), 범례 (Low→High), "리스크" 토글 버튼 (빨강 활성) |
| **산출물** | HexMap 리스크 모드 |
| **의존성** | M11-2, M3-1 |
| **리스크** | 낮음 |
| **DoD** | 리스크 모드 토글 시 색상(초록→빨강)/높이/범례/툴팁 변경 ✓, 빌드 성공 ✓ |

### M11-6: RiskCard 확장 [P0] ✅ DONE (2026-02-13)

| 항목 | 내용 |
|------|------|
| **목적** | 리스크 상세 분석 시각화 |
| **작업** | `frontend/src/components/sidebar/Sidebar.tsx` — RiskCard 섹션 확장. 리스크 스코어 게이지 (0-100, 색상 그라데이션 바). 심각도 배지 (고위험=빨강/주의=노랑/양호=초록). 원인 분해 수평 바차트 (기여도%, 점수 기반 색상, 원시값 표시) |
| **산출물** | 확장된 RiskCard UI |
| **의존성** | M11-1, M3-3 |
| **리스크** | 낮음 |
| **DoD** | 리스크 스코어 게이지 + 분해 차트 + 심각도 배지 표시 ✓, 빌드 성공 ✓ |

### M11-7: AlternativeAreasCard 컴포넌트 [P0] ✅ DONE (2026-02-13)

| 항목 | 내용 |
|------|------|
| **목적** | 대안 구역 추천 시각화 |
| **작업** | `frontend/src/components/sidebar/AlternativeAreasCard.tsx` — 신규. 대안 구역 2곳 카드 (area_name, risk_score, 유동/매출/경쟁 비교 테이블, 리스크 개선폭). 클릭 시 해당 Hex로 맵 이동 + 상세 표시. Sidebar.tsx에 조건부 렌더링 추가 |
| **산출물** | AlternativeAreasCard 컴포넌트 |
| **의존성** | M11-3, M11-6 |
| **리스크** | 낮음 |
| **DoD** | 대안 2곳 비교표 표시 ✓, 클릭 시 맵 이동 ✓, 유동/매출/점포/폐업률 비교 ✓, 리스크 개선폭 표시 ✓ |
