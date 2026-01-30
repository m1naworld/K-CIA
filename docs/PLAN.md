# K-CIA Lite — 프로젝트 실행 계획서 (PLAN.md)

**버전:** 1.0
**작성일:** 2026-01-30
**전략:** 시나리오 1 먼저 완결 → 패턴 재사용으로 확장

---

## A. Scope & Strategy

### MVP 정의: 시나리오 1 "입지 Top3 추천" 완결

**Definition of Done (DoD):**

1. 사용자가 웹에서 성수동 3D Hex 맵(높이=유동, 색=매출증감)을 보고 탐색할 수 있다
2. 업종(디저트/카페) 필터 + 분기 필터가 동작한다
3. Hex 클릭 시 사이드바에 요약 카드 6개(유동/매출/경쟁/성장/리스크/추천) + QoQ 미니차트가 표시된다
4. 챗봇에 "여기 디저트 카페 차려도 될까?"류 질문 → 근거 기반 Top3 추천 + 리스크 + 체크리스트 응답
5. 모든 카드/응답에 as-of 배지(데이터 기준시점)가 표시된다
6. 행정동/상권코드 토글이 동작한다 (영역 기준 전환)
7. 유튜브 모듈 OFF 상태에서 위 모든 기능이 완결된다
8. 골든 쿼리 3종(TopN/QoQ/적합도)이 재현 가능하다

### Non-goals (이번 단계에서 하지 않을 것)

- 시나리오 2~8 구현
- 유튜브/소셜 모듈 (옵션 — Phase 2 이후)
- PDF 보고서 생성/공유 기능
- 사용자 인증/계정 시스템
- D14(실거래가)/D15(임대통계)/D10(지하상가임대) 적재
- 포트폴리오(다점포) 기능
- 모바일 최적화
- 프로덕션 배포 (로컬/스테이징까지만)

### 확정사항 반영 상태

| 확정사항 | 반영 |
|---------|------|
| 행정동 + 상권코드 둘 다 지원(토글) | `dim_area(area_type)` 이원화 + UI 토글 — M1/M3에서 구현 |
| H3 기본 res=9 | `bridge_area_h3_weight` 생성 시 res=9 사용 — M1에서 구현 |
| 유튜브/소셜 OFF여도 Q&A 성립 | Supervisor → SQL Agent + Insight Agent만으로 완결 설계 — M2에서 구현 |
| 후행성 as-of 배지/경고/D11 보정 | 모든 카드에 `data_asof` 표시, D11은 Should(있으면 보정 카드) — M3에서 구현 |
| DB: Postgres + pgvector / Supabase 호환 | DDL은 Supabase 호환 SQL — M0/M1에서 구현 |

### Q3(임대/공실 미시 데이터) 검증 플로우

| 우선순위 | 전략 | 채택 조건 | 대체안 |
|---------|------|----------|--------|
| **P0** | 서울시 우리마을가게 상권분석서비스 "임대시세" API/파일 확인 | 행정동/상권 단위 데이터가 공개 포털에서 접근 가능 | P1으로 전환 |
| **P1** | 한국부동산원 임대동향조사(D16/D17/D18) 거시 통계 배지 | 분기별 파일 다운로드 가능 | P2로 전환 |
| **P2** | 점포 개폐업 비율(D2)로 "공실 리스크(간접)" 산출 | D2 데이터 가용 (이미 Must) | 사용자 입력(가정)으로 대체 |

> **시나리오 1에서는 Q3 불필요.** 시나리오 7/8 진입 시 P0→P1→P2 순서로 검증.

---

## B. Milestones (시나리오 1 중심)

### M0: Repo/Infra 준비

| 항목 | 내용 |
|------|------|
| **입력** | 현재 레포 구조, 기술 스택 확정(Next.js + FastAPI + Supabase) |
| **작업 체크리스트** | |
| | - [ ] 모노레포 디렉토리 구조 확정 (`frontend/`, `backend/`, `etl/`, `docs/`) |
| | - [ ] `docker-compose.yml` 작성 (Postgres/Supabase local, FastAPI, Next.js dev) |
| | - [ ] `.env.example` 작성 (SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY, SEOUL_API_KEY) |
| | - [ ] Next.js 14 프로젝트 초기화 (App Router + TailwindCSS + shadcn/ui) |
| | - [ ] FastAPI 프로젝트 스켈레톤 (health check endpoint) |
| | - [ ] DB 마이그레이션 도구 선정 (Alembic 또는 Supabase migrations) |
| | - [ ] CI lint/format 설정 (Python: ruff, JS: eslint+prettier) |
| **산출물** | `docker-compose.yml`, `frontend/`, `backend/`, `.env.example`, CI config |
| **DoD** | `docker-compose up`으로 Postgres + FastAPI + Next.js 동시 기동, health check 통과 |
| **리스크** | Supabase local vs cloud 선택 — 로컬(supabase CLI)로 시작, 클라우드는 스테이징 시 전환 |

### M1: Data Layer (시나리오 1 최소 데이터셋)

| 항목 | 내용 |
|------|------|
| **입력** | D1, D2, D3, D5, D9 원본 데이터, Postgres 기동 상태 |
| **작업 체크리스트** | |
| | - [ ] DDL 실행: `dim_area`, `dim_category`, `bridge_area_h3_weight`, `fact_sales_area_qtr`, `fact_flow_area_qtr`, `fact_store_area_qtr`, `analysis_run` |
| | - [ ] D9(행정동 SHP) 적재 → `dim_area(area_type='ADMIN_DONG')` |
| | - [ ] D3(상권영역) 적재 → `dim_area(area_type='COMMERCIAL_AREA')` |
| | - [ ] `preset_area_scope` 테이블 생성 + 성수동 프리셋(4개 행정동 + 주요 상권코드) 적재 |
| | - [ ] H3 polyfill(res=9): `dim_area` → `bridge_area_h3_weight` 생성 |
| | - [ ] D1(매출) ETL: raw → `fact_sales_area_qtr` (성수동 필터, 최근 8분기) |
| | - [ ] D5(유동) ETL: raw → `fact_flow_area_qtr` (성수동 필터, 최근 8분기) |
| | - [ ] D2(점포) ETL: raw → `fact_store_area_qtr` (성수동 필터, 최근 8분기) |
| | - [ ] `dim_category` 적재 (서비스_업종_코드 → 명칭 매핑) |
| | - [ ] 품질 체크: coverage(분기별 결측), 이상치(QoQ winsorize), PK 중복 검증 |
| | - [ ] (Should) D11(실시간) 스냅샷 적재기 스켈레톤 (`fact_realtime_congestion_area`) |
| **산출물** | 마이그레이션 SQL, ETL 스크립트(`etl/`), 적재된 DB |
| **DoD** | `SELECT count(*) FROM fact_sales_area_qtr WHERE qtr >= '2025-Q1'` > 0, H3 bridge 행 > 0, 품질 리포트 통과 |
| **리스크** | D5 파일 포맷 변경 가능(공공데이터 비정형) → raw 보관 + 파싱 로직 분리 |

### M2: API Layer (analytics + chat 최소)

| 항목 | 내용 |
|------|------|
| **입력** | M1 완료(DB 적재), FastAPI 스켈레톤 |
| **작업 체크리스트** | |
| | - [ ] `GET /api/map/hexagons` — H3 그리드 + 집계값(유동/매출/점포) 반환 |
| | - [ ] `GET /api/map/hexagon/{h3_index}` — 특정 Hex 상세(6개 카드 데이터) |
| | - [ ] `GET /api/data/categories` — 업종 목록 |
| | - [ ] `GET /api/data/area-scope` — 영역 토글용(행정동/상권 프리셋) |
| | - [ ] `POST /api/chat` — LangGraph 오케스트레이션 (Supervisor → SQL Agent → Insight Agent) |
| | - [ ] SQL Agent 구현: 자연어 → SQL 변환, 허용 테이블/안전규칙 적용 |
| | - [ ] Insight Agent 구현: SQL 결과 → 근거/리스크/추천/체크리스트 구조화 |
| | - [ ] Supervisor 라우터: 정량("매출/인구/TopN") → SQL, 추천("해도 될까/리스크") → Insight |
| | - [ ] 응답에 `data_asof` 필드 포함 |
| | - [ ] 행정동/상권 토글 파라미터(`area_type`) 지원 |
| **산출물** | FastAPI 엔드포인트 5개, LangGraph agent 3개 |
| **DoD** | curl로 hexagons 조회 성공, 챗봇 "디저트 카페 Top3" 질의에 근거 기반 응답 반환, area_type 토글 동작 |
| **리스크** | LLM 비용/레이턴시 — GPT-4o-mini로 시작, 품질 부족 시 GPT-4o 전환 |

### M3: UI Layer (3D Hex + 사이드바 + 챗)

| 항목 | 내용 |
|------|------|
| **입력** | M2 완료(API 동작), Next.js 스켈레톤 |
| **작업 체크리스트** | |
| | - [ ] Deck.gl + react-map-gl 통합: 3D ColumnLayer(H3 기반) |
| | - [ ] Hex elevation=유동/매출, color=매출증감(QoQ) 매핑 |
| | - [ ] 좌측 필터 패널: 업종 선택, 분기 선택, 영역 기준 토글(행정동/상권) |
| | - [ ] Hex 클릭 → 사이드바: 요약 카드 6개 + QoQ 미니차트(Recharts) |
| | - [ ] as-of 배지 컴포넌트 (분기/월/실시간 구분) |
| | - [ ] 챗봇 패널: Vercel AI SDK 기반 스트리밍 UI |
| | - [ ] 챗봇 응답 구조화 렌더링 (근거카드/리스크/추천/체크리스트) |
| | - [ ] (Should) D11 실시간 보정 카드 (후행성 경고 + "실시간 확인" 버튼) |
| | - [ ] Zustand 상태 관리: 선택 Hex, 필터, area_type |
| **산출물** | Next.js 페이지/컴포넌트 |
| **DoD** | 브라우저에서 3D 맵 렌더링 < 3초, Hex 클릭→사이드바 표시, 챗봇 질의→스트리밍 응답 표시, 토글 전환 시 맵 갱신 |
| **리스크** | Deck.gl 초기 로딩 성능 — 데이터 경량화(GeoJSON 최소화) + 레이지 로딩 |

### M4: Eval/Logging (골든쿼리 + 스냅샷 + 이벤트 로그)

| 항목 | 내용 |
|------|------|
| **입력** | M2/M3 완료 |
| **작업 체크리스트** | |
| | - [ ] 골든 쿼리 3종 정의 및 저장: TopN 추천, QoQ 비교, 적합도 점수 |
| | - [ ] 골든 쿼리 회귀 테스트 스크립트 (입력→SQL→결과 비교) |
| | - [ ] `analysis_run` 저장 로직: 질문/필터/SQL/결과/가정/asof 기록 |
| | - [ ] 이벤트 로그 테이블 + 클라이언트 이벤트 전송 (`HEX_CLICK`, `ASK`, `FILTER_APPLY`) |
| | - [ ] SQL Agent 안전규칙 검증 테스트 (DDL/DML 거부, LIMIT 강제) |
| **산출물** | 골든 쿼리 파일, 회귀 테스트, 이벤트 로그 테이블 |
| **DoD** | 골든 쿼리 3종 회귀 테스트 통과, analysis_run에 저장된 결과 조회 가능, 이벤트 로그 1건 이상 기록 |
| **리스크** | 낮음 — 기능 코드 위에 검증 레이어 추가 |

---

## C. Data Ingestion Plan for Scenario 1 (최소셋 우선)

### Must / Should / Could 분류

| 분류 | 데이터셋 | 용도 |
|------|---------|------|
| **Must** | D1 추정매출(상권) | Hex 색상(매출증감), 사이드바 매출 카드, 적합도 점수 |
| **Must** | D5 유동인구(상권) | Hex 높이(유동), 사이드바 유동 카드, 시간대/요일/연령 |
| **Must** | D2 점포(행정동) | 경쟁 카드(점포수/개폐업), 리스크 계산 |
| **Must** | D3 상권영역(공간) | 상권 폴리곤 → H3 매핑, dim_area 적재 |
| **Must** | D9 행정동 경계(SHP) | 행정동 폴리곤 → H3 매핑, dim_area 적재 |
| **Should** | D11 실시간 도시데이터 | 후행성 보정 카드("지금 혼잡도"), 즉시성 UX |
| **Could** | D4 상주인구(행정동) | 수요 보강(배후 인구), 시나리오 1에서는 비필수 |
| **Could** | D8 집객시설(상권배후지) | 맥락 보강(학교/문화시설), 시나리오 3에서 주로 사용 |

### 데이터셋별 상세

#### D1 추정매출(상권) — Must

| 항목 | 내용 |
|------|------|
| 소스 | 서울 열린데이터광장 OA-15572, CSV/파일 다운로드 |
| 키 | `기준_년분기_코드` + `상권_코드` + `서비스_업종_코드` |
| 수집 방식 | 전체 다운로드 → 성수동 상권코드 필터 → 증분(분기 추가) |
| 멱등성 키(PK) | `(area_id, qtr, cat_id)` — area_id는 상권코드 lookup |
| 갱신 주기 | 분기 1회 (약 1~3개월 후행) |
| 품질 체크 | 분기별 상권코드 coverage ≥ 90%, 매출액 null < 5%, QoQ 이상치 winsorize |
| 저장 | raw: `raw_sales` → normalized: `fact_sales_area_qtr` → mart: H3 집계 뷰 |
| H3 매핑 | 필요 — `bridge_area_h3_weight` 경유 |

#### D5 유동인구(상권) — Must

| 항목 | 내용 |
|------|------|
| 소스 | data.go.kr 15094719, CSV 파일 다운로드 |
| 키 | `기준_년분기_코드` + `상권_코드` (+ 시간대/요일/성별/연령대) |
| 수집 방식 | 전체 다운로드 → 성수동 필터 → 증분(분기 추가) |
| 멱등성 키(PK) | `(area_id, qtr)` — 시간대/요일/성별/연령은 JSONB breakdown |
| 갱신 주기 | 분기 1회 (약 1~3개월 후행) |
| 품질 체크 | 분기 결측 여부, 유동인구 0 이하 이상치, 시간대 24개 완비 여부 |
| 저장 | raw: `raw_flow` → normalized: `fact_flow_area_qtr` → mart: H3 집계 뷰 |
| H3 매핑 | 필요 |

#### D2 점포(행정동) — Must

| 항목 | 내용 |
|------|------|
| 소스 | 서울 열린데이터광장 OA-22172, CSV/API |
| 키 | `기준_년분기_코드` + `행정동_코드` + `서비스_업종_코드` |
| 수집 방식 | 전체 → 성수동 행정동코드 필터 |
| 멱등성 키(PK) | `(area_id, qtr, cat_id)` — area_id는 행정동코드 lookup |
| 갱신 주기 | 분기 1회 |
| 품질 체크 | 점포수 ≥ 0, 폐업 ≤ 점포, 개업+기존-폐업 ≈ 다음분기 점포 |
| 저장 | raw: `raw_store` → normalized: `fact_store_area_qtr` |
| H3 매핑 | 필요 — D2는 행정동 기반이므로 D9 폴리곤 경유 H3 매핑 |

#### D3 상권영역(공간) — Must

| 항목 | 내용 |
|------|------|
| 소스 | 서울 열린데이터광장 OA-15560, SHP/좌표(EPSG:5181) |
| 키 | `상권_코드` (공간정보) |
| 수집 방식 | 전체 다운로드 → EPSG:5181→4326 변환 → 성수동 필터 |
| 멱등성 키(PK) | `(area_type='COMMERCIAL_AREA', area_code)` |
| 갱신 주기 | 비정기 (상권 경계 변경 시) |
| 품질 체크 | 폴리곤 유효성(ST_IsValid), 성수동 범위 내 상권코드 수 |
| 저장 | `dim_area` (geom 컬럼) |
| H3 매핑 | 이 데이터 자체가 H3 매핑의 소스 |

#### D9 행정동 경계(SHP) — Must

| 항목 | 내용 |
|------|------|
| 소스 | data.go.kr 15125055, SHP 파일 |
| 키 | 행정동코드(속성), 폴리곤(공간) |
| 수집 방식 | 전체 다운로드 → 성수동 4개 동 필터 |
| 멱등성 키(PK) | `(area_type='ADMIN_DONG', area_code)` |
| 갱신 주기 | 연 1회 (경계 변경 시) |
| 품질 체크 | 4개 동 폴리곤 존재 확인 |
| 저장 | `dim_area` (geom 컬럼) |
| H3 매핑 | 이 데이터 자체가 H3 매핑의 소스 |

#### D11 실시간 도시데이터 — Should

| 항목 | 내용 |
|------|------|
| 소스 | 서울 열린데이터광장 OA-21285, REST API (실시간) |
| 키 | `AREA_NM` 또는 `AREA_CD`, `PPLTN_TIME` |
| 수집 방식 | 5~10분 간격 스냅샷 적재 (성수동 관련 장소만) |
| 멱등성 키(PK) | `(area_id, ts)` |
| 갱신 주기 | 실시간 (분/시간 단위) |
| 품질 체크 | 성수동 장소 매핑 여부 확인(120장소 중 해당 장소 존재 여부) |
| 저장 | `fact_realtime_congestion_area` |
| H3 매핑 | 장소→좌표→H3 근사 매핑 (정밀도 낮음, 보정 배지 수준) |

---

## D. Backlog 확장 로드맵

### 시나리오 1 패턴 재사용 관점의 확장 그룹

| 확장 그룹 | 시나리오 | 추가 필요 요소 | 재사용 가능 요소 |
|----------|---------|--------------|----------------|
| **G1: 시간대 분석 확장** | S2(피크타임 운영전략) | 시간대/요일 히트맵 UI, 운영 파라미터 입력 | D5 시간대 데이터(이미 적재), SQL Agent, Insight Agent |
| **G2: 타겟 필터 확장** | S3(팝업 위치·기간) | 연령/성별 필터, D8(집객시설), 타겟 가중치 | Hex맵, 사이드바, 챗봇 전체 |
| **G3: 기간 비교 확장** | S4(분기 비교 리포트) | QoQ 비교 UI(2축 차트), 상대 비교 로직 | D1/D5 QoQ 계산(이미 있음), SQL Agent |
| **G4: 리스크 진단 확장** | S5(경쟁과밀/폐업 리스크) | 리스크 레이어(색=폐업), 리스크 분해 카드 | D2 점포 데이터(이미 적재), Hex맵, Insight Agent |
| **G5: 콘텐츠 생성 확장** | S6(4컷/쇼츠 구조화) | 스토리 모드 UI, 4컷 텍스트+이미지 생성 (Gemini Nano Banana) | analysis_run 결과 재사용, Insight Agent |
| **G6: 포트폴리오 확장** | S7(다점포 리밸런싱), S8(A/B 투자 검토) | dim_asset, D14/D15, 포트폴리오 매트릭스 UI | Hex맵 + 핀 오버레이, SQL/Insight Agent |

### 추천 확장 순서

```
Phase 1: S1 (MVP) ← 현재
Phase 2: S2 + S5 (시간대 + 리스크 — D5/D2 재사용, UI 확장만)
Phase 3: S3 + S4 (타겟 필터 + 기간 비교 — D8 추가, 비교 UI)
Phase 4: S6 (콘텐츠 생성 — Gemini Nano Banana 기반 4컷/쇼츠)
Phase 5: S7 + S8 (포트폴리오 — D14/D15 추가, dim_asset, Q3 검증)
```

### 유튜브 옵션 모듈

| 항목 | 내용 |
|------|------|
| **붙이는 시점** | Phase 3 이후 (공공데이터 기반 시나리오 4개 이상 안정화 후) |
| **OFF일 때 전략** | Supervisor가 Social Agent를 스킵, Insight Agent가 공공데이터 근거 + "추가 확인 체크리스트(현장/리뷰/검색)" 제공, as-of 배지에 "소셜 데이터 미포함" 명시 |
| **ON 최소 요구** | `fact_youtube_trend_day_scope` 테이블, Social Agent, 감성 분석 파이프라인 |

---

## ASSUMPTIONS (가정 목록)

| ID | 가정 | 영향 | 재검토 조건 |
|----|------|------|-----------|
| A1 | 서울 열린데이터광장 CSV 다운로드가 자동화 가능(URL 패턴 일정) | ETL 방식 | API 변경 시 |
| A2 | 성수동 관련 D11 장소가 120개 중 1개 이상 존재 | D11 적재 가능 여부 | 장소 목록 확인 시 |
| A3 | D5 유동인구 파일이 상권코드 기준으로 성수동 필터 가능 | ETL 필터링 | 파일 스키마 확인 시 |
| A4 | GPT-4o-mini가 SQL 생성 품질 충분 (90% 성공률 목표) | LLM 비용 | 골든 쿼리 테스트 시 |
| A5 | Supabase 로컬(CLI)이 PostGIS + h3-pg 확장 지원 | 공간 연산 | M0 셋업 시 확인 |
| A6 | Next.js dev 서버 + FastAPI + Postgres가 단일 docker-compose로 기동 가능 | 개발 환경 | M0 셋업 시 확인 |
| A7 | D2(점포-행정동)를 상권 단위로 매핑할 때 D9-D3 공간조인 오차가 허용 범위 | 경쟁 데이터 정확도 | M1 품질 체크 시 |
| A8 | DataIngestionPlan은 `K-CIA_Lite_DataIngestionPlan.md`로 별도 존재 — 수집 아키텍처/의사코드/메타 테이블은 해당 문서 기준 | 참조 문서 | 수집 설계 변경 시 |
