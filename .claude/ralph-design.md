# K-CIA Lite — Phase 2~5 확장 설계 문서

**작성일:** 2026-02-07
**범위:** PLAN.md 추천 확장 순서 Phase 2~5

---

## 변경 개요

Phase 1(S1 MVP)에서 구축한 3D Hex맵 + 사이드바 + 챗봇 아키텍처 위에 S2~S8 시나리오를 확장 구현.
기존 D1/D2/D3/D5/D9/D11 데이터를 최대한 재사용하고, 필요한 데이터(D8/D14/D15)는 크롤링 또는 별도 정리.

---

## Phase 2: S2(피크타임 운영전략) + S5(리스크 진단)

### S2: 피크타임 기반 운영전략

**핵심**: D5의 `flow_by_hour`, `flow_by_weekday`, `flow_by_demo` JSONB 데이터를 활용하여 시간대/요일 분석.

#### Backend 변경

1. **`backend/api/map.py` — 시간대 히트맵 API 추가**
   - `GET /api/map/hexagons/heatmap?area_type=&qtr=&mode=hourly|weekday`
   - `mode=hourly`: 24시간대별 유동인구 반환
   - `mode=weekday`: 7요일별 유동인구 반환
   - 응답: `{ data: [{ h3_index, lat, lng, area_name, values: {0: N, 1: N, ...} }] }`

2. **`backend/api/map.py` — 피크타임 분석 API 추가**
   - `GET /api/map/hexagon/{h3_index}/peaktime?qtr=`
   - 응답: `{ peak_hours: [14, 15, 16], off_peak_hours: [6, 7, 8], weekday_pattern: {...}, demo_breakdown: {...} }`

3. **`backend/api/schemas.py` — 신규 스키마**
   - `HeatmapHexagon`, `HeatmapResponse`
   - `PeaktimeAnalysis`
   - `OperationPlan` (운영 권장 카드)

4. **`backend/agents/sql_agent.py` — 시간대 쿼리 가이드 추가**
   - flow_by_hour/flow_by_weekday JSONB 쿼리 패턴 추가
   - 예: `flow_by_hour->>'14' AS hour_14_flow`

5. **`backend/agents/insight_agent.py` — 운영전략 응답 템플릿 추가**
   - 피크타임 기반 인력/프로모션 권장
   - 운영 파라미터(객단가/회전율) 기반 계산

#### Frontend 변경

6. **`frontend/src/components/map/HeatmapLayer.tsx` — 신규**
   - 시간대/요일 히트맵 레이어 (DeckGL HeatmapLayer 또는 색상 그라데이션)
   - 시간대 슬라이더 UI

7. **`frontend/src/components/sidebar/PeaktimeCard.tsx` — 신규**
   - 피크타임 3개 / 오프피크 2개 자동 표시
   - 시간대별 유동인구 차트 (Recharts BarChart)

8. **`frontend/src/components/sidebar/OperationCard.tsx` — 신규**
   - 운영 파라미터 입력 (객단가, 좌석수, 회전율)
   - 권장 스케줄 카드

9. **`frontend/src/store/mapStore.ts` — 상태 추가**
   - `viewMode: 'default' | 'heatmap_hourly' | 'heatmap_weekday' | 'risk'`
   - `selectedHour: number | null`
   - `operationParams: { avgTicket, seats, turnoverRate }`

10. **`frontend/src/components/filters/FilterPanel.tsx` — 뷰 모드 토글 추가**
    - "기본" / "시간대 히트맵" / "리스크" 모드 전환

### S5: 경쟁과밀/폐업 리스크 진단

**핵심**: D2(점포/개폐업) + D1(매출) 기반 리스크 스코어 계산.

#### Backend 변경

11. **`backend/api/map.py` — 리스크 레이어 API 추가**
    - `GET /api/map/hexagons/risk?area_type=&category=&qtr=`
    - 리스크 스코어 = `w1*폐업QoQ + w2*점포증가율 + w3*매출QoQ(-) + w4*경쟁밀도`
    - 응답에 `risk_score`, `risk_factors` 포함

12. **`backend/api/map.py` — 리스크 분해 API 추가**
    - `GET /api/map/hexagon/{h3_index}/risk?category=&qtr=`
    - 원인 기여도(폐업/점포/매출/유동) 분해
    - 대안 구역 2곳 추천 (리스크 낮고 수요 충분한 곳)

13. **`backend/api/schemas.py` — 리스크 스키마**
    - `RiskAnalysis(risk_score, risk_factors, alternative_areas)`

#### Frontend 변경

14. **`frontend/src/components/map/HexMap.tsx` — 리스크 레이어 모드 추가**
    - 리스크 모드: `color=폐업률/포화`, `elevation=매출`
    - 색상 스케일: 낮은 리스크(초록) → 높은 리스크(빨강)

15. **`frontend/src/components/sidebar/RiskAnalysisCard.tsx` — 신규**
    - 리스크 분해 카드 (원인 3개 기여도 바)
    - 대안 구역 제안 카드
    - 고객 제안용 결론/근거/주의사항 템플릿

---

## Phase 3: S3(팝업 위치·기간) + S4(분기 비교 리포트)

### S3: 팝업 스토어 위치·기간·시간대 결정

**핵심**: D5의 연령/성별 breakdown을 활용한 타겟 필터 + D8(집객시설) 맥락 보강.

#### 데이터 추가

16. **D8 집객시설(상권배후지) — ETL**
    - `etl/load_d8_facilities.py` — 신규
    - 서울 열린데이터광장 OA-15581 API
    - 테이블: `fact_facilities_area(area_id, qtr, facility_type, facility_cnt)`
    - facility_type: 전시/문화/학교/대형마트/교통 등

17. **`backend/migrations/004_phase2_extensions.sql` — DDL**
    - `fact_facilities_area` 테이블 생성

#### Backend 변경

18. **`backend/api/map.py` — 팝업 모드 API**
    - `GET /api/map/hexagons/popup?target_age=20-34&target_gender=F&day_type=weekend&qtr=`
    - 타겟층 유동비중 가중치 적용 → 후보 Hex 랭킹
    - D8 집객시설 수 맥락 포함

19. **`backend/api/schemas.py` — 팝업 스키마**
    - `PopupRecommendation(area_name, target_flow_ratio, peak_hours, facility_context)`

20. **`backend/agents/sql_agent.py` — 타겟 필터 쿼리 패턴 추가**
    - flow_by_demo JSONB에서 연령/성별 추출 패턴
    - `flow_by_demo->'age_20_34'->>'male'`

#### Frontend 변경

21. **`frontend/src/components/filters/PopupFilterPanel.tsx` — 신규**
    - 타겟 연령 선택 (20대, 30대, 40대...)
    - 타겟 성별 선택
    - 주말/평일 강조 토글
    - 기간 선택 (1일, 2일, 1주)

22. **`frontend/src/components/sidebar/PopupCard.tsx` — 신규**
    - 타겟 유입 시간대 Top3
    - 근거 표 (유동/성별/연령)
    - 집객시설 맥락 카드

### S4: 분기 비교 리포트

**핵심**: 기존 QoQ 계산 로직 확장 + 2축 비교 차트 UI.

#### Backend 변경

23. **`backend/api/map.py` — 기간 비교 API**
    - `GET /api/map/hexagon/{h3_index}/compare?qtr1=&qtr2=`
    - 두 분기 간 유동/매출/점포 변화율 + 전체 성수동 평균 대비 상대 비교
    - 시간대/요일별 세부 변화 분석

24. **`backend/api/schemas.py` — 비교 스키마**
    - `QuarterComparison(metric, qtr1_value, qtr2_value, change_rate, avg_change_rate, above_avg)`

#### Frontend 변경

25. **`frontend/src/components/charts/CompareChart.tsx` — 신규**
    - 2축 차트 (Recharts ComposedChart: 유동 Bar + 매출 Line)
    - 분기 비교 프리셋 (전분기 vs 이번분기)
    - "증감 원인 후보" 카드 (시간대/요일 변화 하이라이트)

26. **`frontend/src/components/sidebar/ComparePanel.tsx` — 신규**
    - 비교 기간 선택 UI
    - KPI 3개 + 리스크 2개 + 다음 실험 2개

---

## Phase 4: S6(콘텐츠 생성 — 4컷/쇼츠)

**핵심**: analysis_run 결과를 재사용하여 "설득용 스토리" 텍스트 산출물 생성.

#### 데이터/API 키 필요
- **Gemini API Key** (GEMINI_API_KEY) — 별도 문서 정리 필요

#### Backend 변경

27. **`backend/agents/content_agent.py` — 신규**
    - Gemini Nano Banana API 연동 (또는 GPT-4o fallback)
    - 입력: KPI 3개 + 기준시점 + 목표(입지추천/리스크경고/운영최적화)
    - 출력: 4컷 구조 (훅/팩트/리스크/액션) 텍스트 + 각 컷 근거 KPI
    - "공공데이터 후행/추정치" 문구 자동 포함

28. **`backend/api/content.py` — 신규 엔드포인트**
    - `POST /api/content/story` — 4컷 스토리 생성
    - `POST /api/content/script` — 60초 스크립트 생성
    - 입력: `{ analysis_run_id, message_goal, kpis }`

29. **`backend/agents/graph.py` — Content Agent 노드 추가**
    - Supervisor에 "스토리/콘텐츠/4컷/쇼츠" 라우팅 규칙 추가

30. **`backend/api/schemas.py` — 콘텐츠 스키마**
    - `StoryRequest`, `StoryResponse(cuts: list[StoryCut], citations, asof)`
    - `StoryCut(title, body, kpi_ref, visual_hint)`

#### Frontend 변경

31. **`frontend/src/components/content/StoryMode.tsx` — 신규**
    - "스토리 모드" 버튼 (선택 구역/업종/기간 기반)
    - 핵심 메시지 목표 선택 (입지추천/리스크경고/운영최적화)
    - 4컷 구조 프리뷰 + 편집
    - 텍스트 다운로드/공유 + 스냅샷 저장

32. **`frontend/src/components/content/StoryCutCard.tsx` — 신규**
    - 개별 컷 카드 (훅/팩트/리스크/액션)
    - 근거 KPI 배지 표시
    - 기준 분기 자동 표기

---

## Phase 5: S7(다점포 리밸런싱) + S8(A/B 투자 검토)

### 데이터 추가

33. **D14 실거래가 — ETL** (API Key 필요)
    - `etl/load_d14_realprice.py` — 신규
    - data.go.kr 15126463 OpenAPI
    - 테이블: `fact_real_price(area_id, contract_ym, price_per_sqm, floor, building_age)`

34. **D15 임대료/공실률 — ETL**
    - `etl/load_d15_rent.py` — 신규
    - 서울 열린데이터광장 OA-12553
    - 테이블: `fact_rent_vacancy(area_id, qtr, rent_per_sqm, vacancy_rate, yield_rate)`

35. **`backend/migrations/005_portfolio.sql` — DDL**
    - `dim_asset(asset_id, user_id, address, lat, lng, h3_index, category, area_id)` — 점포 등록
    - `fact_real_price`, `fact_rent_vacancy`
    - `portfolio_snapshot(snapshot_id, user_id, assets_json, metrics_json, recommendations_json, created_at)`

#### Backend 변경

36. **`backend/api/portfolio.py` — 신규 엔드포인트**
    - `POST /api/portfolio/assets` — 점포 등록 (주소→좌표→H3 매핑)
    - `GET /api/portfolio/health` — 점포별 Health 카드 (Green/Yellow/Red)
    - `GET /api/portfolio/matrix` — 포트폴리오 매트릭스 (성과×리스크)
    - `POST /api/portfolio/compare` — A/B 비교

37. **`backend/api/schemas.py` — 포트폴리오 스키마**
    - `AssetInput`, `AssetHealth`, `PortfolioMatrix`, `ABComparison`

38. **건강도 산출 로직** (`backend/services/portfolio_service.py` — 신규)
    - `health = 수요(z) - 경쟁(z) + 성장(z) - 폐업리스크(z)`
    - k-ring(1~2) 내 지표 평균/추세(QoQ)
    - 철수/확장 트리거(임계값)

#### Frontend 변경

39. **`frontend/src/components/portfolio/PortfolioPanel.tsx` — 신규**
    - "내 점포" 업로드/입력 (주소/업종)
    - 지도에 핀 + 주변 Hex 리스크/기회 오버레이
    - 점포별 Health 카드 (Green/Yellow/Red)

40. **`frontend/src/components/portfolio/MatrixChart.tsx` — 신규**
    - 포트폴리오 매트릭스 (Recharts ScatterChart: 성과 vs 리스크)
    - 리밸런싱 제안 3안

41. **`frontend/src/components/portfolio/ABCompare.tsx` — 신규**
    - A/B 비교 탭 (수요/경쟁/성장/리스크/가격)
    - 민감도 시뮬레이션 (임대료/공실 변동)

42. **`frontend/src/store/portfolioStore.ts` — 신규**
    - 점포 목록 상태 관리
    - health/matrix 데이터

---

## 파일별 변경 요약

### 신규 파일 (Backend)
| 파일 | Phase | 용도 |
|------|-------|------|
| `backend/migrations/004_phase2_extensions.sql` | 2-3 | 시설/리스크 테이블 DDL |
| `backend/migrations/005_portfolio.sql` | 5 | 포트폴리오 테이블 DDL |
| `backend/api/content.py` | 4 | 콘텐츠 생성 API |
| `backend/api/portfolio.py` | 5 | 포트폴리오 API |
| `backend/agents/content_agent.py` | 4 | Content Agent |
| `backend/services/portfolio_service.py` | 5 | 건강도 계산 서비스 |

### 수정 파일 (Backend)
| 파일 | Phase | 변경 |
|------|-------|------|
| `backend/api/map.py` | 2, 3 | 히트맵/리스크/팝업/비교 API 추가 |
| `backend/api/schemas.py` | 2-5 | 신규 스키마 추가 |
| `backend/agents/sql_agent.py` | 2, 3 | 시간대/타겟 쿼리 패턴 추가 |
| `backend/agents/insight_agent.py` | 2 | 운영전략 응답 템플릿 추가 |
| `backend/agents/supervisor.py` | 4 | 콘텐츠 라우팅 추가 |
| `backend/agents/graph.py` | 4 | Content Agent 노드 추가 |
| `backend/main.py` | 4, 5 | 라우터 등록 |

### 신규 파일 (Frontend)
| 파일 | Phase | 용도 |
|------|-------|------|
| `frontend/src/components/map/HeatmapLayer.tsx` | 2 | 시간대/요일 히트맵 |
| `frontend/src/components/sidebar/PeaktimeCard.tsx` | 2 | 피크타임 카드 |
| `frontend/src/components/sidebar/OperationCard.tsx` | 2 | 운영 파라미터 입력 |
| `frontend/src/components/sidebar/RiskAnalysisCard.tsx` | 2 | 리스크 분해 카드 |
| `frontend/src/components/filters/PopupFilterPanel.tsx` | 3 | 팝업 필터 |
| `frontend/src/components/sidebar/PopupCard.tsx` | 3 | 팝업 추천 카드 |
| `frontend/src/components/charts/CompareChart.tsx` | 3 | 2축 비교 차트 |
| `frontend/src/components/sidebar/ComparePanel.tsx` | 3 | 비교 패널 |
| `frontend/src/components/content/StoryMode.tsx` | 4 | 스토리 모드 |
| `frontend/src/components/content/StoryCutCard.tsx` | 4 | 4컷 카드 |
| `frontend/src/components/portfolio/PortfolioPanel.tsx` | 5 | 포트폴리오 |
| `frontend/src/components/portfolio/MatrixChart.tsx` | 5 | 매트릭스 차트 |
| `frontend/src/components/portfolio/ABCompare.tsx` | 5 | A/B 비교 |
| `frontend/src/store/portfolioStore.ts` | 5 | 포트폴리오 상태 |

### 수정 파일 (Frontend)
| 파일 | Phase | 변경 |
|------|-------|------|
| `frontend/src/store/mapStore.ts` | 2, 3 | viewMode, 시간대 선택, 운영 파라미터 |
| `frontend/src/components/map/HexMap.tsx` | 2 | 리스크 모드, 히트맵 모드 |
| `frontend/src/components/filters/FilterPanel.tsx` | 2, 3 | 뷰 모드 토글, 팝업 필터 |
| `frontend/src/components/sidebar/Sidebar.tsx` | 2, 3 | 피크타임/리스크/팝업/비교 카드 통합 |
| `frontend/src/app/page.tsx` | 4, 5 | 스토리모드/포트폴리오 패널 추가 |
| `frontend/src/types/map.ts` | 2-5 | 신규 타입 추가 |

### 신규 파일 (ETL)
| 파일 | Phase | 용도 |
|------|-------|------|
| `etl/load_d8_facilities.py` | 3 | D8 집객시설 ETL |
| `etl/load_d14_realprice.py` | 5 | D14 실거래가 ETL |
| `etl/load_d15_rent.py` | 5 | D15 임대료/공실 ETL |

---

## 예상 엣지케이스

1. **flow_by_hour/flow_by_weekday JSONB가 NULL**: 일부 상권에서 시간대 데이터 없을 수 있음 → NULL 안전 처리, "데이터 없음" 표시
2. **D8 API 응답 없음**: 성수동 상권배후지 코드가 API와 불일치할 수 있음 → 상권코드 매핑 검증 필요
3. **리스크 스코어 0 제곱근**: 폐업/개업 모두 0인 경우 → 0 처리, "데이터 부족" 경고
4. **Gemini API 불안정**: Content Agent에서 Gemini API 실패 시 → GPT-4o fallback 로직
5. **점포 좌표→H3 매핑 실패**: 잘못된 좌표 → 서울 범위 검증 + fallback
6. **D14 실거래가 없는 구역**: 최근 거래 없을 수 있음 → "거래 이력 없음" 배지
7. **JSONB 키 이름 불일치**: flow_by_demo의 키 형식이 데이터셋마다 다를 수 있음 → 파싱 로직에 유연한 키 매칭

---

## 데이터 크롤링/API 키 필요 사항 (별도 정리)

### 크롤링 가능 (API 키 있음)
- **D8 집객시설**: SEOUL_API_KEY 사용 (이미 존재) — Phase 3에서 직접 크롤링
- **D11 실시간**: SEOUL_API_KEY 사용 (이미 구현) — 기존 코드 재사용

### API 키 필요 (별도 발급)
- **D14 실거래가**: data.go.kr 공공데이터포털 API 키 (REALPRICE_API_KEY) — Phase 5
- **Gemini API**: GEMINI_API_KEY — Phase 4

### 기존 데이터 재사용
- **D1 매출**: fact_sales_area_qtr (4,681행) — 모든 Phase
- **D2 점포**: fact_store_area_qtr (ADMIN_DONG 2,195행 + COMMERCIAL_AREA 6,985행) — Phase 2, 5
- **D5 유동인구**: fact_flow_area_qtr (92행, flow_by_hour/weekday/demo JSONB) — Phase 2, 3

### 파일 다운로드 (API 불필요)
- **D15 임대료/공실**: 서울 열린데이터광장에서 CSV 다운로드 — Phase 5
