# K-CIA Lite — Phase 2~5 테스트 계획

**작성일:** 2026-02-07
**범위:** Phase 2-5 Backend API 엔드포인트 + 헬퍼 함수 + 프론트엔드 빌드

---

## 테스트 전략

### 접근방식
1. **Backend Unit Tests** (pytest): 헬퍼 함수, 스키마 검증, 비즈니스 로직 직접 테스트
2. **Backend API Tests** (FastAPI TestClient): DB mock으로 엔드포인트 HTTP 레벨 테스트
3. **Frontend Build Test**: TypeScript 컴파일 + Next.js 빌드 성공 확인

### 테스트 환경
- pytest 8.3.4 (로컬 설치됨)
- FastAPI TestClient (httpx 기반, DB 의존성 오버라이드)
- DB mock: `app.dependency_overrides[get_db]` 패턴 사용
- LLM mock: `unittest.mock.patch` 으로 content_agent, agents 모킹

---

## T1: 헬퍼 함수 단위 테스트

### T1-1: `_prev_quarter()` (map.py)
| # | 입력 | 예상 출력 | 설명 |
|---|------|----------|------|
| 1 | `"20243"` | `"20242"` | 일반 분기 |
| 2 | `"20241"` | `"20234"` | Q1→이전년 Q4 |
| 3 | `"20251"` | `"20244"` | 연도 넘어감 |
| 4 | `"20244"` | `"20243"` | Q4→Q3 |

### T1-2: `_safe_div()` (map.py)
| # | 입력 (a, b) | 예상 출력 | 설명 |
|---|------------|----------|------|
| 1 | `(110, 100)` | `0.1` | 정상 |
| 2 | `(100, 0)` | `None` | 제로 나눗셈 |
| 3 | `(None, 100)` | `None` | None 입력 |
| 4 | `(100, None)` | `None` | None 입력 |
| 5 | `(0, 100)` | `-1.0` | 0에서 감소 |

### T1-3: Pydantic 스키마 검증
| # | 스키마 | 테스트 | 설명 |
|---|--------|------|------|
| 1 | `StoryRequest` | 기본값 검증 | goal="입지추천", kpis={} |
| 2 | `AssetInput` | 필수 필드 | address 필수 |
| 3 | `ChatRequest` | question min_length=1 | 빈 문자열 거부 |
| 4 | `RiskHexagon` | 기본값 0.0 | risk_score 기본값 |
| 5 | `PortfolioMatrix` | 빈 리스트 | assets=[] 유효 |

---

## T2: Map API 엔드포인트 테스트 (Phase 2)

### T2-1: GET /api/map/hexagons/heatmap
| # | 입력 | 예상 | 설명 |
|---|------|------|------|
| 1 | `?mode=hourly&area_type=COMMERCIAL_AREA` | 200 + HeatmapResponse | 정상 - 시간대 모드 |
| 2 | `?mode=weekday&area_type=ADMIN_DONG` | 200 + HeatmapResponse | 정상 - 요일 모드 |
| 3 | `?mode=hourly` (데이터 없음) | 200 + data=[] | 빈 결과 |
| 4 | 빈 flow_by_hour JSONB | 200 + values={} | NULL JSONB 처리 |

### T2-2: GET /api/map/hexagon/{h3_index}/peaktime
| # | 입력 | 예상 | 설명 |
|---|------|------|------|
| 1 | 유효 H3 + 데이터 있음 | 200 + PeaktimeAnalysis | 정상 |
| 2 | 유효 H3 + 유동 데이터 없음 | 404 | "No flow data" |
| 3 | 잘못된 H3 문자열 | 400 | "Invalid H3 index" |
| 4 | peak_hours 검증 | len(peak_hours)==3 | 상위 3시간 |
| 5 | off_peak_hours 검증 | len(off_peak_hours)==3 | 하위 3시간 |

### T2-3: GET /api/map/hexagons/risk
| # | 입력 | 예상 | 설명 |
|---|------|------|------|
| 1 | 기본 파라미터 | 200 + RiskLayerResponse | 정상 |
| 2 | 업종 필터 | 200 + 필터된 결과 | category 필터 동작 |
| 3 | 리스크 스코어 범위 | 모든 score ∈ [0, 1] | 범위 검증 |
| 4 | 데이터 없는 경우 | 200 + data=[] | 빈 결과 |

### T2-4: GET /api/map/hexagon/{h3_index}/risk
| # | 입력 | 예상 | 설명 |
|---|------|------|------|
| 1 | 유효 H3 | 200 + RiskAnalysis | 정상 |
| 2 | 잘못된 H3 | 400 | 에러 |
| 3 | 존재하지 않는 H3 | 404 | 스코프 밖 |
| 4 | alternative_areas 검증 | len<=2 | 최대 2개 대안 |
| 5 | alternative 정렬 | risk_score 오름차순 | 낮은 리스크 우선 |

---

## T3: Compare API 테스트 (Phase 3)

### T3-1: GET /api/map/hexagon/{h3_index}/compare
| # | 입력 | 예상 | 설명 |
|---|------|------|------|
| 1 | 유효 H3 + qtr1 + qtr2 | 200 + CompareResponse | 정상 |
| 2 | 잘못된 H3 | 400 | 에러 |
| 3 | H3 스코프 밖 | 404 | 에러 |
| 4 | 같은 분기 비교 | 200 + change_rate=0 | 동일 분기 |
| 5 | 데이터 없는 분기 | 200 + values=None | 부분 데이터 |
| 6 | comparisons 메트릭 수 | 6개 (sales_amt, sales_cnt, flow_total, store_cnt, open_cnt, close_cnt) | 메트릭 완전성 |
| 7 | above_avg 검증 | change_rate > avg → true | 상대 비교 |

---

## T4: Content API 테스트 (Phase 4)

### T4-1: POST /api/content/story
| # | 입력 | 예상 | 설명 |
|---|------|------|------|
| 1 | 기본 요청 (goal만) | 200 + StoryResponse | 정상 (LLM mock) |
| 2 | 4컷 구조 검증 | cuts 길이 4 | 4컷 완전성 |
| 3 | cut_number 검증 | 1,2,3,4 순서 | 순서 보장 |
| 4 | citations 존재 | list 타입 | 출처 포함 |
| 5 | warning 기본값 | "본 자료는..." 포함 | 면책 조항 |
| 6 | analysis_run_id 연동 | KPI 주입 | DB에서 KPI 조회 |

---

## T5: Portfolio API 테스트 (Phase 5)

### T5-1: POST /api/portfolio/assets
| # | 입력 | 예상 | 설명 |
|---|------|------|------|
| 1 | 유효한 좌표 | 200 + asset_id | 정상 등록 |
| 2 | lat/lng 없음 | 400 | "lat and lng are required" |
| 3 | 성수동 범위 좌표 | H3 인덱스 반환 | H3 변환 검증 |

### T5-2: GET /api/portfolio/health
| # | 입력 | 예상 | 설명 |
|---|------|------|------|
| 1 | 점포 존재 | 200 + PortfolioMatrix | 정상 |
| 2 | 점포 없음 | 200 + assets=[] | 빈 결과 |
| 3 | health_status 범위 | green/yellow/red 중 하나 | 상태 검증 |
| 4 | health_score 범위 | 0 <= score <= 1 | 범위 검증 |
| 5 | suggestions 로직 | red 있으면 경고 포함 | 경고 메시지 |
| 6 | stdev > 0.2 | 리밸런싱 제안 포함 | 편차 경고 |

### T5-3: POST /api/portfolio/compare
| # | 입력 | 예상 | 설명 |
|---|------|------|------|
| 1 | 유효한 두 점포 | 200 + ABComparison | 정상 |
| 2 | 없는 점포 ID | 404 | "Asset not found" |
| 3 | recommendation 내용 | A 또는 B 추천 포함 | 비교 결과 |
| 4 | sensitivity 포함 | "D14/D15" 언급 | 데이터 부족 안내 |

---

## T6: Agent 라우팅 테스트 (Phase 4)

### T6-1: Supervisor "content" 라우팅
| # | 입력 질문 | 예상 route | 설명 |
|---|----------|-----------|------|
| 1 | "4컷 스토리 만들어줘" | "content" | 콘텐츠 키워드 |
| 2 | "쇼츠 스크립트 생성" | "content" | 쇼츠 키워드 |
| 3 | "성수동 매출 Top3" | "both" 또는 "sql" | 일반 질의 |

### T6-2: Content Agent 노드
| # | 입력 state | 예상 | 설명 |
|---|-----------|------|------|
| 1 | 정상 state | content_brief 포함 | 4컷 생성 |
| 2 | 빈 sql_result | 여전히 4컷 | fallback |
| 3 | JSON 파싱 실패 | 단일 컷 fallback | 에러 복구 |

---

## T7: 프론트엔드 빌드 테스트

### T7-1: TypeScript 컴파일
- `tsc --noEmit` → 0 errors

### T7-2: Next.js 빌드
- `next build` → 성공

### T7-3: ESLint
- `eslint` → warning 0개

---

## 엣지케이스 정리

| # | 엣지케이스 | 테스트 ID | 검증 방법 |
|---|-----------|----------|----------|
| 1 | JSONB NULL (flow_by_hour) | T2-1 #4 | values={} 반환 |
| 2 | 제로 나눗셈 (QoQ) | T1-2 #2 | None 반환 |
| 3 | 존재하지 않는 H3 | T2-2 #3, T2-4 #2 | 400/404 |
| 4 | 데이터 없는 분기 | T3-1 #5 | None values |
| 5 | LLM JSON 파싱 실패 | T6-2 #3 | fallback 컷 |
| 6 | 좌표 없는 점포 등록 | T5-1 #2 | 400 에러 |
| 7 | 점포 0개 포트폴리오 | T5-2 #2 | 빈 배열 |
| 8 | 리스크 스코어 범위 초과 | T2-3 #3 | cap 0-1 |

---

## 파일 구조

```
tests/
├── __init__.py                    # 기존
├── golden_queries/                # 기존
│   └── golden_queries.json
├── test_sql_agent.py              # 기존 (Phase 1)
├── conftest.py                    # 신규 — DB mock, TestClient 설정
├── test_map_helpers.py            # 신규 — T1 헬퍼 함수
├── test_schemas.py                # 신규 — T1-3 스키마 검증
├── test_map_heatmap.py            # 신규 — T2 히트맵/피크타임/리스크
├── test_map_compare.py            # 신규 — T3 분기 비교
├── test_content.py                # 신규 — T4 콘텐츠 생성
├── test_portfolio.py              # 신규 — T5 포트폴리오
└── test_frontend_build.py         # 신규 — T7 프론트엔드 빌드
```

## 예상 테스트 수: ~45 테스트 케이스
