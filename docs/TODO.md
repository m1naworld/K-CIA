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

## ~~M5: 점포 수 기반 H3 Weight~~ — 삭제됨 (2026-02-07)

> 불필요로 판단하여 삭제. 면적 기반 weight만 사용.

---

## M6: S3 Data + Backend (D8 ETL + 인구통계 필터)

### M6-1: DB Migration (fact_facility_area_qtr) [P0]

| 항목 | 내용 |
|------|------|
| **목적** | D8 집객시설 데이터 저장 테이블 생성 |
| **작업** | `backend/migrations/004_s3_facility.sql` 작성 (fact_facility_area_qtr) |
| **산출물** | Migration SQL |
| **의존성** | M1-1 |
| **리스크** | 낮음 |
| **DoD** | 테이블 생성 확인 |

### M6-2: D8 ETL (집객시설) [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 집객시설 데이터 수집 및 적재 |
| **작업** | `etl/load_facility_api.py` — Seoul API `VwsmTrdarHitterIndQq` → fact_facility_area_qtr. seoul_api_collector에 D8_FACILITY 서비스 추가 |
| **산출물** | ETL 스크립트, 적재 데이터 |
| **의존성** | M6-1 |
| **리스크** | API 컬럼 매핑 확인 필요 |
| **DoD** | fact_facility_area_qtr 적재, 시설 유형별 건수 조회 |

### M6-3: Hexagons API 인구통계 필터 [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 팝업 모드에서 타겟 인구 기반 필터링 |
| **작업** | `backend/api/map.py` — target_gender, target_age, mode 파라미터 추가. popup mode SQL (flow_by_demo JSONB 추출) |
| **산출물** | 확장된 hexagons API |
| **의존성** | M2-1 |
| **리스크** | JSONB 쿼리 성능 |
| **DoD** | popup mode API 호출 시 target_flow, target_flow_ratio 반환 |

### M6-4: Hexagon Detail 확장 (시설 + 인구통계 카드) [P0]

| 항목 | 내용 |
|------|------|
| **목적** | Hex 상세에 시설/인구통계/시간대 추천 카드 추가 |
| **작업** | `backend/api/schemas.py` — FacilityCard, DemoCard, TimeSlotRecommendation. `backend/api/map.py` — hexagon detail에 추가 필드 |
| **산출물** | 확장된 hexagon detail API |
| **의존성** | M6-1, M6-2, M6-3 |
| **리스크** | 낮음 |
| **DoD** | hexagon detail 응답에 facility, demo, time_slot 필드 포함 |

### M6-5: SQL Agent 프롬프트 업데이트 [P0]

| 항목 | 내용 |
|------|------|
| **목적** | SQL Agent가 인구통계/시설 질의 처리 가능 |
| **작업** | `backend/agents/sql_agent.py` — flow_by_demo JSONB 패턴, fact_facility_area_qtr 스키마, ALLOWED_TABLES 추가 |
| **산출물** | 업데이트된 SQL Agent |
| **의존성** | M6-1 |
| **리스크** | 낮음 |
| **DoD** | "20대 여성 유동인구 Top3" 질의에 JSONB 추출 SQL 생성 |

---

## M7: S3 Frontend (팝업 모드 UI)

### M7-1: Zustand Store 확장 [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 팝업 모드 상태 관리 |
| **작업** | `frontend/src/store/mapStore.ts` — mode, targetGender, targetAge, setMode, setTargetGender, setTargetAge |
| **산출물** | 확장된 Zustand store |
| **의존성** | M3-2 |
| **리스크** | 낮음 |
| **DoD** | 팝업 모드 상태 전환 동작 |

### M7-2: TypeScript 타입 추가 [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 새 인터페이스 타입 안전성 |
| **작업** | `frontend/src/types/map.ts` — FacilityCard, DemoCard, TimeSlotRecommendation, HexagonSummary/DetailResponse 확장 |
| **산출물** | TypeScript 타입 |
| **의존성** | 없음 |
| **리스크** | 낮음 |
| **DoD** | npm run build 타입 에러 없음 |

### M7-3: 팝업 모드 필터 UI [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 팝업 모드 전환 + 타겟 필터 선택 |
| **작업** | `frontend/src/components/filters/PopupModePanel.tsx` — Default/Popup 토글, 성별 선택, 연령대 선택. FilterPanel.tsx에 통합 |
| **산출물** | PopupModePanel 컴포넌트 |
| **의존성** | M7-1 |
| **리스크** | 낮음 |
| **DoD** | 팝업 모드 토글 동작, 필터 파라미터 API 전달 |

### M7-4: 사이드바 카드 추가 (3개) [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 팝업 모드 상세 정보 |
| **작업** | FacilityCard.tsx, DemoCard.tsx, TimeSlotCard.tsx. Sidebar.tsx에 popup 모드 조건부 렌더링 |
| **산출물** | 사이드바 카드 3개 |
| **의존성** | M6-4, M7-1 |
| **리스크** | 낮음 |
| **DoD** | popup 모드 사이드바에 3개 카드 표시 |

### M7-5: HexMap 팝업 모드 시각화 [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 팝업 모드 시각 구분 |
| **작업** | `frontend/src/components/map/HexMap.tsx` — popup mode: elevation=target_flow, color=target_flow_ratio (파랑→보라) |
| **산출물** | 확장된 HexMap |
| **의존성** | M7-1, M6-3 |
| **리스크** | 낮음 |
| **DoD** | popup 모드에서 색상/높이 변경 확인 |

---

## M8: S4 분기 비교

### M8-1: 비교 API [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 2개 분기 지표 비교 |
| **작업** | `backend/api/map.py` — POST /api/map/compare. `backend/api/schemas.py` — ComparisonRequest, ComparisonMetrics, ComparisonResponse |
| **산출물** | 비교 API 엔드포인트 |
| **의존성** | M2-1 |
| **리스크** | 낮음 |
| **DoD** | 2개 분기 비교 API 호출 시 changes 반환 |

### M8-2: SQL Agent 비교 쿼리 패턴 [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 분기 비교 자연어 질의 처리 |
| **작업** | `backend/agents/sql_agent.py` — 분기 비교 SQL 패턴 (WITH before AS, after AS) |
| **산출물** | 업데이트된 SQL Agent |
| **의존성** | M6-5 |
| **리스크** | 낮음 |
| **DoD** | "2024Q3 대비 Q4 매출 변화" 질의에 비교 SQL 생성 |

### M8-3: Frontend 비교 모드 [P0]

| 항목 | 내용 |
|------|------|
| **목적** | 비교 모드 UI |
| **작업** | Zustand: comparisonMode, compareQtrBefore/After. ComparisonPanel.tsx, ComparisonCard.tsx, ComparisonChart.tsx. Sidebar.tsx 조건부 렌더링 |
| **산출물** | 비교 UI 컴포넌트 |
| **의존성** | M8-1 |
| **리스크** | 낮음 |
| **DoD** | 비교 모드에서 Before/After 카드 + 차트 렌더링 |

---

## M9: SNS Module (YouTube + Naver)

### M9-1: DB Migration (SNS 테이블) [P0]

| 항목 | 내용 |
|------|------|
| **목적** | SNS 데이터 저장 구조 |
| **작업** | `backend/migrations/005_sns_module.sql` — fact_social_trend_daily, social_module_config |
| **산출물** | Migration SQL |
| **의존성** | M1-1 |
| **리스크** | 낮음 |
| **DoD** | 테이블 생성, social_module_config 기본값(enabled=false) |

### M9-2: YouTube Collector + Loader [P0]

| 항목 | 내용 |
|------|------|
| **목적** | YouTube 트렌드 데이터 수집 |
| **작업** | `etl/collectors/youtube_collector.py`, `etl/load_youtube_trends.py` — YouTube Data API v3, 키워드 검색, 일별 버즈/감성 |
| **산출물** | YouTube ETL |
| **의존성** | M9-1, YOUTUBE_API_KEY |
| **리스크** | 무료 할당량 (10K units/day) |
| **DoD** | "성수동 카페" 키워드 검색 → fact_social_trend_daily 적재 |

### M9-3: Naver Collector + Loader [P0]

| 항목 | 내용 |
|------|------|
| **목적** | Naver Blog/Cafe 트렌드 수집 |
| **작업** | `etl/collectors/naver_collector.py`, `etl/load_naver_trends.py` — Naver Search API, 키워드 검색 |
| **산출물** | Naver ETL |
| **의존성** | M9-1, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET |
| **리스크** | 낮음 (25K calls/day) |
| **DoD** | "성수동 맛집" 키워드 → fact_social_trend_daily 적재 |

### M9-4: Social Agent (LangGraph) [P0]

| 항목 | 내용 |
|------|------|
| **목적** | SNS 데이터 분석 에이전트 |
| **작업** | `backend/agents/social_agent.py` — 모듈 ON/OFF 분기, 트렌드 요약/감성/키워드. `backend/agents/graph.py` — Social Agent 노드 추가. `backend/agents/insight_agent.py` — social_result 통합 |
| **산출물** | Social Agent |
| **의존성** | M9-1, M2-3 |
| **리스크** | 모듈 OFF 회귀 테스트 |
| **DoD** | SNS ON → 정성 근거 포함, SNS OFF → 기존 동작 유지 |

### M9-5: Social API Endpoint [P0]

| 항목 | 내용 |
|------|------|
| **목적** | SNS 데이터 API |
| **작업** | `backend/api/social.py` — GET /api/social/trends, GET /api/social/config |
| **산출물** | Social API 엔드포인트 |
| **의존성** | M9-1 |
| **리스크** | 낮음 |
| **DoD** | /api/social/config 응답, /api/social/trends 데이터 반환 |

### M9-6: Frontend SNS UI [P0]

| 항목 | 내용 |
|------|------|
| **목적** | SNS 데이터 시각화 |
| **작업** | Zustand: socialEnabled, socialOverlay, socialData. `frontend/src/types/social.ts`. SocialToggle, SocialBuzzCard, KeywordCloudCard, EvidenceSnippetsCard. 맵 상단 성수동 전체 SNS 요약 배지 |
| **산출물** | SNS UI 컴포넌트 |
| **의존성** | M9-5 |
| **리스크** | H3 매핑 불가 → 전체 지역 수준 표시 |
| **DoD** | SNS ON → 사이드바에 소셜 카드 표시 |
