# K-CIA Lite — Phase 2~5 확장 구현 결과 보고서

**작성일:** 2026-02-07
**작성자:** Ralph Loop (자동화 구현)
**범위:** PLAN.md 추천 확장 순서 Phase 2~5 (S2, S3, S4, S5, S6, S7, S8)

---

## 1. 요약

Phase 1(S1 MVP: 입지 Top3 추천)에서 구축한 3D Hex맵 + 사이드바 + 챗봇 아키텍처 위에 7개 시나리오(S2~S8)를 확장 구현했습니다.

| Phase | 시나리오 | 상태 |
|-------|---------|------|
| Phase 2 | S2 피크타임 운영전략 | DONE |
| Phase 2 | S5 경쟁과밀/폐업 리스크 진단 | DONE |
| Phase 3 | S3 팝업 스토어 위치·기간 | DONE (Backend API) |
| Phase 3 | S4 분기 비교 리포트 | DONE |
| Phase 4 | S6 콘텐츠 생성 (4컷/쇼츠) | DONE |
| Phase 5 | S7 다점포 리밸런싱 | DONE |
| Phase 5 | S8 A/B 투자 검토 | DONE |

**총 변경:** 신규 20파일 + 수정 13파일 = 약 4,000줄 코드

---

## 2. 구현 상세

### 2.1 Phase 2: S2 피크타임 운영전략

**목적:** D5 유동인구의 `flow_by_hour`, `flow_by_weekday`, `flow_by_demo` JSONB 데이터를 활용하여 시간대/요일별 분석 제공

**Backend API:**
- `GET /api/map/hexagons/heatmap?mode=hourly|weekday` — 시간대/요일별 유동인구 히트맵
- `GET /api/map/hexagon/{h3_index}/peaktime` — 피크/오프피크 시간대 자동 분석

**Frontend UI:**
- `PeaktimeCard` — 피크 시간대 배지 + 24시간 미니 바 차트 + 요일별 유동인구
- `HexMap` 히트맵 모드 — 시간대 슬라이더(0~23시)로 실시간 색상 변경
- `FilterPanel` 뷰 모드 토글 — 기본/시간대히트맵/요일히트맵/리스크

**Agent 확장:**
- SQL Agent에 `flow_by_hour->>'14'` 등 JSONB 쿼리 패턴 추가
- Insight Agent에 운영전략 응답 템플릿 추가 (peak_analysis, recommendations)

### 2.2 Phase 2: S5 리스크 진단

**목적:** D2(점포/개폐업) + D1(매출) 기반 리스크 스코어 계산 및 시각화

**리스크 스코어 공식:**
```
risk = 0.3 * normalized_close_rate
     + 0.2 * normalized_store_growth
     + 0.3 * normalized_sales_decline
     + 0.2 * normalized_flow_decline
```

**Backend API:**
- `GET /api/map/hexagons/risk` — 리스크 레이어 (전체 Hex 스코어)
- `GET /api/map/hexagon/{h3_index}/risk` — 리스크 분해 + 대안 구역 2곳 제안

**Frontend UI:**
- `RiskAnalysisCard` — 리스크 게이지 바, 위험 요인 목록, 지표 분해, 대안 구역 제안
- `HexMap` 리스크 모드 — 초록(양호)→노랑(주의)→빨강(위험) 색상 스케일

### 2.3 Phase 3: S4 분기 비교 리포트

**목적:** 두 분기 간 유동/매출/점포 변화율 비교 + 성수동 평균 대비 상대 비교

**Backend API:**
- `GET /api/map/hexagon/{h3_index}/compare?qtr1=&qtr2=` — 6개 메트릭 변화율 + 평균 대비

**Frontend UI:**
- `ComparePanel` — 분기 선택 드롭다운 2개 + 비교 버튼
- `CompareChart` — 수평 바 차트 (증가=초록, 감소=빨강) + 평균 이상/이하 배지

### 2.4 Phase 3: D8 집객시설 ETL

**ETL 스크립트:** `etl/load_d8_facilities.py`
- 서울 열린데이터광장 API (기존 SEOUL_API_KEY 사용)
- 20개 시설 유형 (관광시설, 교통시설, 지하철역, 대형마트 등)
- `fact_facilities_area` 테이블에 적재

**DDL:** `backend/migrations/004_phase2_extensions.sql`
- `fact_facilities_area(area_id, qtr, facility_type, facility_cnt)`
- `content_brief(brief_id, ...)` 콘텐츠 저장 테이블

### 2.5 Phase 4: S6 콘텐츠 생성

**목적:** analysis_run 결과를 재사용하여 "설득용 4컷 스토리" 텍스트 산출물 생성

**Backend:**
- `content_agent.py` — GPT-4o 기반 4컷 구조 생성 (HOOK/FACT/RISK/ACTION)
- `POST /api/content/story` — 4컷 스토리 생성 + content_brief 테이블 저장
- Supervisor에 "content" 라우팅 추가 (4컷/쇼츠/스토리 키워드)
- LangGraph에 content_agent 노드 추가 (sql → content → END)

**Frontend UI:**
- `StoryMode` — 메시지 목표 선택 (입지추천/리스크경고/운영최적화) + 생성 버튼
- `StoryCutCard` — 개별 컷 카드 (색상 구분, KPI 배지, visual_hint)

### 2.6 Phase 5: S7/S8 포트폴리오

**목적:** 다점포 운영자를 위한 포트폴리오 건강도 모니터링 + A/B 투자 비교

**건강도 산출:**
```
health = demand * 0.4 - competition * 0.2 - close_risk * 0.2 + growth * 0.3
```
- k-ring(1) 내 지표 평균 사용
- Green: 70+, Yellow: 40-70, Red: <40

**Backend API:**
- `POST /api/portfolio/assets` — 점포 등록 (주소 → H3 매핑)
- `GET /api/portfolio/health` — 점포별 Health 카드
- `POST /api/portfolio/compare` — A/B 비교

**Frontend UI:**
- `PortfolioPanel` — 점포 등록 폼 + Health 카드 리스트
- `MatrixChart` — 수요 vs 리스크 ScatterChart (사분면 분석)
- `ABCompare` — A/B 점포 선택 + 지표별 비교 테이블

**DDL:** `backend/migrations/005_portfolio.sql`
- `dim_asset`, `fact_real_price`, `fact_rent_vacancy`, `portfolio_snapshot`

---

## 3. 파일 목록

### 3.1 신규 파일

| 파일 | Phase | 용도 |
|------|-------|------|
| `backend/migrations/004_phase2_extensions.sql` | 2-3 | 시설/콘텐츠 DDL |
| `backend/migrations/005_portfolio.sql` | 5 | 포트폴리오 DDL |
| `backend/agents/content_agent.py` | 4 | Content Agent |
| `backend/api/content.py` | 4 | 콘텐츠 생성 API |
| `backend/api/portfolio.py` | 5 | 포트폴리오 API |
| `etl/load_d8_facilities.py` | 3 | D8 집객시설 ETL |
| `etl/load_d14_realprice.py` | 5 | D14 실거래가 ETL |
| `etl/load_d15_rent.py` | 5 | D15 임대료/공실 ETL |
| `frontend/src/components/sidebar/PeaktimeCard.tsx` | 2 | 피크타임 카드 |
| `frontend/src/components/sidebar/RiskAnalysisCard.tsx` | 2 | 리스크 분해 카드 |
| `frontend/src/components/sidebar/ComparePanel.tsx` | 3 | 비교 패널 |
| `frontend/src/components/charts/CompareChart.tsx` | 3 | 비교 차트 |
| `frontend/src/components/content/StoryMode.tsx` | 4 | 스토리 모드 |
| `frontend/src/components/content/StoryCutCard.tsx` | 4 | 4컷 카드 |
| `frontend/src/components/portfolio/PortfolioPanel.tsx` | 5 | 포트폴리오 패널 |
| `frontend/src/components/portfolio/MatrixChart.tsx` | 5 | 매트릭스 차트 |
| `frontend/src/components/portfolio/ABCompare.tsx` | 5 | A/B 비교 |
| `frontend/src/components/ui/input.tsx` | 5 | shadcn/ui Input |
| `frontend/src/store/portfolioStore.ts` | 5 | 포트폴리오 상태 |

### 3.2 수정 파일

| 파일 | Phase | 변경 |
|------|-------|------|
| `backend/api/map.py` | 2, 3 | +5 엔드포인트 (heatmap, peaktime, risk, risk-detail, compare) |
| `backend/api/schemas.py` | 2-5 | +15 Pydantic 모델 |
| `backend/agents/sql_agent.py` | 2, 3 | 시간대/타겟 JSONB 쿼리 패턴 |
| `backend/agents/insight_agent.py` | 2 | 운영전략/리스크 응답 템플릿 |
| `backend/agents/supervisor.py` | 4 | "content" 라우팅 추가 |
| `backend/agents/graph.py` | 4 | content_agent 노드 + content_brief 상태 |
| `backend/main.py` | 4, 5 | content_router, portfolio_router 등록 |
| `backend/api/chat.py` | 4 | content_brief SSE 이벤트 |
| `frontend/src/types/map.ts` | 2-5 | +12 TypeScript 인터페이스 |
| `frontend/src/store/mapStore.ts` | 2, 3 | viewMode, peaktime, risk, compare 상태/액션 |
| `frontend/src/components/map/HexMap.tsx` | 2 | 리스크/히트맵 레이어 + 슬라이더 |
| `frontend/src/components/filters/FilterPanel.tsx` | 2 | 뷰 모드 토글 |
| `frontend/src/components/sidebar/Sidebar.tsx` | 2, 3 | 신규 카드 통합 |
| `frontend/src/app/page.tsx` | 4, 5 | StoryMode, PortfolioPanel 추가 |

---

## 4. 데이터 필요사항 (별도 정리)

### 4.1 기존 데이터 재사용 (추가 작업 불필요)

| 데이터셋 | 테이블 | 행 수 | 사용 Phase |
|---------|--------|-------|-----------|
| D1 매출 | fact_sales_area_qtr | 4,681 | 2, 3, 5 |
| D2 점포 | fact_store_area_qtr | 9,180 | 2, 5 |
| D3 상권영역 | dim_area | 23 | 전체 |
| D5 유동인구 | fact_flow_area_qtr | 92 | 2, 3 |
| D9 행정동 | dim_area | 4 | 전체 |
| D11 실시간 | fact_realtime_congestion_area | 2 | 전체 |

### 4.2 신규 데이터 — 크롤링 가능 (API 키 있음)

| 데이터셋 | Phase | API | API 키 | ETL 스크립트 | 상태 |
|---------|-------|-----|--------|------------|------|
| D8 집객시설 | 3 | 서울 열린데이터광장 OA-15581 | SEOUL_API_KEY (기존) | `etl/load_d8_facilities.py` | 코드 완료, 실행 대기 |

### 4.3 신규 데이터 — API 키 발급 필요

| 데이터셋 | Phase | API | 필요 API 키 | ETL 스크립트 | 발급 방법 |
|---------|-------|-----|-----------|------------|----------|
| D14 실거래가 | 5 | data.go.kr 15126463 | `REALPRICE_API_KEY` | `etl/load_d14_realprice.py` | data.go.kr 회원가입 → '국토부 상업용 부동산 임대차 정보' 활용 신청 → 승인 후 발급 |

### 4.4 신규 데이터 — 파일 다운로드 (API 키 불필요)

| 데이터셋 | Phase | 출처 | ETL 스크립트 | 다운로드 방법 |
|---------|-------|------|------------|-------------|
| D15 임대료/공실률 | 5 | 서울 열린데이터광장 OA-12553 | `etl/load_d15_rent.py` | https://data.seoul.go.kr/dataList/OA-12553/F/1/datasetView.do 에서 CSV 다운로드 → `data/raw/d15_rent/` 디렉토리 배치 |

### 4.5 API 키 — 선택 (콘텐츠 생성용)

| 용도 | Phase | 필요 API 키 | 현재 상태 |
|------|-------|-----------|----------|
| Gemini 4컷/쇼츠 | 4 | `GEMINI_API_KEY` | GPT-4o fallback 구현됨. Gemini 사용 시 별도 발급 필요 |

---

## 5. 환경변수 추가 사항

`.env`에 추가해야 할 변수:

```bash
# Phase 4: 콘텐츠 생성 (선택 — GPT-4o fallback 존재)
GEMINI_API_KEY=          # Gemini Nano Banana API

# Phase 5: 실거래가 데이터 (선택 — 포트폴리오 기능 강화 시)
REALPRICE_API_KEY=       # data.go.kr 공공데이터포털 API 키
```

---

## 6. 실행 순서

### 6.1 DB 마이그레이션

```bash
# Phase 2-3 테이블
psql -U kcia -d kcia -f backend/migrations/004_phase2_extensions.sql

# Phase 5 테이블
psql -U kcia -d kcia -f backend/migrations/005_portfolio.sql
```

### 6.2 데이터 적재

```bash
# D8 집객시설 (SEOUL_API_KEY 필요)
docker compose run --rm --entrypoint python etl -m etl.load_d8_facilities

# D14 실거래가 (REALPRICE_API_KEY 필요)
REALPRICE_API_KEY=... docker compose run --rm --entrypoint python etl -m etl.load_d14_realprice

# D15 임대료/공실 (CSV 수동 다운로드 후)
docker compose run --rm --entrypoint python etl -m etl.load_d15_rent
```

### 6.3 서버 실행

```bash
# Backend
cd backend && uvicorn main:app --reload

# Frontend
cd frontend && npm run dev
```

---

## 7. 커밋 이력

| 커밋 | 내용 |
|------|------|
| `02ac844` | feat(backend): Add Phase 2-5 API endpoints and agent extensions |
| `6c619b8` | feat(frontend,etl): Add Phase 2-5 UI components and ETL scripts |

---

## 8. 알려진 제한사항

1. **D8 집객시설 API 서비스명**: `VwsmTrdarFlpopQq`는 추정 서비스명. 실제 API 호출 시 서비스명 확인 필요
2. **Gemini API 미연동**: Content Agent가 GPT-4o fallback 사용. Gemini Nano Banana 연동 시 별도 작업 필요
3. **포트폴리오 주소→좌표 변환**: 현재 더미 좌표 사용. 실서비스 시 Kakao/Naver 지오코딩 API 연동 필요
4. **D14/D15 데이터 미적재**: ETL 코드 완료, API 키/CSV 파일 확보 후 실행 필요
5. **S3 팝업 전용 UI**: 팝업 필터 패널(타겟 연령/성별/기간)은 미구현. 현재 챗봇으로 대체 가능

---

## 9. 다음 단계 제안

1. **D8 ETL 실행**: SEOUL_API_KEY로 집객시설 데이터 적재
2. **E2E 테스트**: 각 Phase 주요 시나리오별 통합 테스트
3. **S3 팝업 전용 UI**: PopupFilterPanel (타겟 연령/성별/기간 선택) 구현
