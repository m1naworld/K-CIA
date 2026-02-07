# K-CIA Lite — 실행용 작업 티켓 (TODO.md)

**작성일:** 2026-01-30
**전략:** 시나리오 1 우선 → M0~M4 순차 진행

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

## M5: 점포 수 기반 H3 Weight

### M5-1: DB 스키마 추가 [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 점포 기반 weight 저장 구조 |
| **작업** | `backend/migrations/003_store_h3_weight.sql` 작성 및 실행 |
| **산출물** | `raw_semas_store`, `fact_store_h3_count`, `bridge_area_h3_weight_store` 3개 테이블 |
| **의존성** | M1-1 |
| **리스크** | 낮음 |
| **DoD** | 3개 테이블 생성 확인 |

### M5-2: 소상공인 API Collector [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 점포 좌표 수집 |
| **작업** | `etl/collectors/semas_api_collector.py` 구현 |
| **산출물** | SemasAPICollector 클래스 |
| **의존성** | M5-1 |
| **리스크** | API 키 필요 (SEMAS_API_KEY) |
| **DoD** | 성수동 4개 동 점포 조회 성공 |

### M5-3: 점포 수집 ETL [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 점포 데이터 적재 |
| **작업** | `etl/load_semas_stores.py` 구현 |
| **산출물** | raw_semas_store 테이블 적재 |
| **의존성** | M5-2 |
| **리스크** | 좌표 검증 필요 (서울 범위) |
| **DoD** | raw_semas_store 1000건 이상 적재 |

### M5-4: H3 점포 집계 [P0]

| 항목 | 내용 |
|------|------|
| **목적** | H3별 점포 수 계산 |
| **작업** | `etl/load_store_h3_count.py` 구현 |
| **산출물** | fact_store_h3_count 테이블 적재 |
| **의존성** | M5-3 |
| **리스크** | 낮음 |
| **DoD** | fact_store_h3_count 적재, H3 50개 이상 |

### M5-5: 점포 기반 Weight 계산 [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 상권별 H3 weight 계산 |
| **작업** | `etl/compute_store_weight.py` 구현 |
| **산출물** | bridge_area_h3_weight_store 테이블 적재 |
| **의존성** | M5-4, M1-3 (기존 H3 매핑) |
| **리스크** | 점포 0인 상권 fallback 처리 |
| **DoD** | bridge_area_h3_weight_store 적재, weight 합계=1 검증 |

### M5-6: API 수정 [P0]

| 항목 | 내용 |
|------|------|
| **목적** | weight_type 파라미터 지원 |
| **작업** | `backend/api/map.py` 수정 |
| **산출물** | `/api/map/hexagons?weight_type=store\|area` |
| **의존성** | M5-5 |
| **리스크** | 낮음 |
| **DoD** | `/api/map/hexagons?weight_type=store` 응답 정상 |

### M5-7: 품질 검증 [P1]

| 항목 | 내용 |
|------|------|
| **목적** | 데이터 품질 확인 |
| **작업** | 면적 vs 점포 weight 비교 리포트 |
| **산출물** | 검증 쿼리 + 비교 문서 |
| **의존성** | M5-6 |
| **리스크** | 낮음 |
| **DoD** | 비교 쿼리 실행, 차이점 문서화 |

---

## M6: Phase 2~5 확장 (S2~S8 시나리오)

### M6-1: S2 피크타임 운영전략 + S5 리스크 진단 [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | 시간대별 운영전략 및 경쟁과밀/폐업 리스크 진단 |
| **작업** | Backend: heatmap API, peaktime API, risk 레이어/상세 API. Frontend: PeaktimeCard, RiskAnalysisCard, 뷰모드 토글(기본/히트맵/리스크), HexMap 리스크·히트맵 레이어 |
| **산출물** | `backend/api/map.py` (수정), `PeaktimeCard.tsx`, `RiskAnalysisCard.tsx`, `FilterPanel.tsx` (수정), `HexMap.tsx` (수정) |
| **의존성** | M2-1, M3-1 |
| **DoD** | 뷰모드 토글 동작, 피크타임 카드 표시, 리스크 분해 카드 표시 |

### M6-2: S3 팝업 위치·기간 + S4 분기 비교 리포트 [P0] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | 분기간 비교 분석 및 D8 집객시설 데이터 확보 |
| **작업** | Backend: compare API. Frontend: CompareChart, ComparePanel. ETL: load_d8_facilities.py |
| **산출물** | `CompareChart.tsx`, `ComparePanel.tsx`, `etl/load_d8_facilities.py` |
| **의존성** | M2-1 |
| **DoD** | 분기 비교 차트 표시, D8 ETL 스크립트 실행 가능 |

### M6-3: S6 콘텐츠 생성 (4컷/쇼츠) [P1] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | 상권 분석 결과를 4컷 스토리로 변환 |
| **작업** | Backend: content_agent, POST /api/content/story. Frontend: StoryCutCard, StoryMode. LangGraph content 노드 추가 |
| **산출물** | `backend/agents/content_agent.py`, `backend/api/content.py`, `StoryCutCard.tsx`, `StoryMode.tsx` |
| **의존성** | M2-3 |
| **DoD** | 스토리 생성 요청 → 4컷 카드 렌더링 |

### M6-4: S7 다점포 리밸런싱 + S8 A/B 투자 검토 [P1] ✅ DONE (2026-02-07)

| 항목 | 내용 |
|------|------|
| **목적** | 다점포 포트폴리오 건강도 및 A/B 비교 |
| **작업** | Backend: portfolio API (등록/health/compare). Frontend: PortfolioPanel, MatrixChart, ABCompare, portfolioStore. ETL: load_d14_realprice, load_d15_rent |
| **산출물** | `backend/api/portfolio.py`, `PortfolioPanel.tsx`, `MatrixChart.tsx`, `ABCompare.tsx`, `portfolioStore.ts` |
| **의존성** | M2-1 |
| **DoD** | 점포 등록 → Health 카드 → A/B 비교 → 매트릭스 차트 |
