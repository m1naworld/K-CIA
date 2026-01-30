# CLAUDE.md — K-CIA Lite 프로젝트 가이드

이 파일은 Claude가 K-CIA Lite 프로젝트에서 작업할 때 따라야 할 컨텍스트와 규칙입니다.

---

## 프로젝트 개요

**K-CIA Lite** — 성수동 하이퍼로컬 상권 분석 AI 플랫폼

- **한 줄 정의**: "성수동의 어제와 오늘을 3D 지도와 대화로 읽어주는 AI 컨설턴트"
- **핵심**: 공공데이터(정량) 기반 인사이트. 유튜브/소셜은 옵션 모듈(OFF여도 모든 Q&A 성립)
- **타겟**: 예비 창업자, 브랜드/마케팅 실무자, 상권 컨설턴트, 임대/투자자
- **현재 단계**: Planning Complete → 시나리오 1(P1 입지 Top3 추천) 구현 진입

---

## 확정사항 (반드시 준수)

1. **영역 기준**: 행정동 + 상권코드 둘 다 지원. UI 토글로 전환. `dim_area(area_type)` 이원화
2. **H3 해상도**: 기본 res=9. 성능 문제 시 res=8 / 정밀 분석 시 res=10 실험 플래그
3. **유튜브/소셜**: 옵션 모듈. OFF여도 모든 Q&A/추천이 공공데이터만으로 성립해야 함
4. **후행성 UX**: 모든 카드/응답에 as-of 배지(데이터 기준시점) 표시. D11(실시간) 보정 카드 제공
5. **DB**: PostgreSQL + PostGIS + pgvector / Supabase 호환

---

## 기술 스택

### Frontend
| 기술 | 용도 |
|-----|-----|
| Next.js 14 (App Router) | React 기반 풀스택 프레임워크 |
| Deck.gl + react-map-gl | WebGL 기반 3D 지도 시각화 |
| TailwindCSS | 유틸리티 퍼스트 CSS |
| shadcn/ui | 재사용 가능한 UI 컴포넌트 |
| Recharts | 차트 시각화 |
| Zustand | 경량 상태 관리 |
| TypeScript | 타입 안전성 |

### Backend
| 기술 | 용도 |
|-----|-----|
| Python 3.11+ | 메인 런타임 |
| FastAPI | REST API 서버 |
| LangChain + LangGraph | LLM 오케스트레이션 |
| OpenAI GPT-4o-mini (→ 4o 에스컬레이션) | LLM 추론 |
| Vercel AI SDK | 챗봇 스트리밍 |

### Database & Infra
| 기술 | 용도 |
|-----|-----|
| Supabase (PostgreSQL + PostGIS + pgvector) | 관계형 DB + 벡터 검색 |
| Docker | 컨테이너화 |
| GitHub Actions | CI/CD |

### Content Gen
| 기술 | 용도 |
|-----|-----|
| Gemini Nano Banana | 4컷 만화/쇼츠 콘텐츠 생성 (Phase 4) |

### Data Sources
- 서울시 공공데이터(D1/D2/D3/D5/D9/D11)
- YouTube Data API (옵션)

---

## 프로젝트 구조

```
K-CIA/
├── CLAUDE.md                          # 현재 파일
├── README.md
├── K-CIA Lite.md                      # PRD
├── K-CIA_Lite_UserScenarios.md        # 유저 시나리오 8개
├── K-CIA_Lite_DataPlan.md             # 데이터 기획 (스키마/LLM/검증)
├── K-CIA_Lite_DataIngestionPlan.md    # 데이터 수집 상세 계획
├── docs/
│   ├── PLAN.md                        # 실행 계획서 (마일스톤/데이터셋/확장)
│   ├── TODO.md                        # 작업 티켓 (M0~M4)
│   ├── PROGRESS.md                    # 진행상황 로그
│   ├── DECISIONS.md                   # 의사결정 로그
│   └── ui.md                          # UI/UX 코딩 표준 (프론트엔드 필수 참고)
├── frontend/                          # Next.js 앱 (구현 예정)
│   └── src/
│       ├── app/                       # App Router pages
│       ├── components/                # React 컴포넌트
│       │   ├── ui/                    # shadcn/ui 컴포넌트
│       │   ├── map/                   # Deck.gl 맵 (HexMap 등)
│       │   ├── chat/                  # 챗봇 UI
│       │   ├── sidebar/              # 필터/상세 패널
│       │   └── charts/               # Recharts 차트
│       ├── store/                     # Zustand stores
│       ├── lib/                       # 유틸리티
│       └── types/                     # TypeScript 타입
├── backend/                           # FastAPI 서버 (구현 예정)
│   ├── api/                           # map, chat, data, events 엔드포인트
│   ├── agents/                        # supervisor, sql_agent, insight_agent, graph
│   └── services/                      # DB 접근, analysis_logger
├── etl/                               # 데이터 파이프라인 (구현 예정)
│   ├── collectors/                    # seoul_zip, boundary, nowcast 수집기
│   ├── processors/                    # sales, flow, store, h3_mapper 처리기
│   └── quality/                       # 품질 체크 스크립트
├── tests/
│   ├── golden_queries/                # 골든 쿼리 3종
│   └── test_sql_agent.py
├── docker-compose.yml
└── .env.example
```

---

## 진행 방식 (필수)

1. **Plan 먼저**: 코딩 전에 항상 계획/설계 확인. `docs/PLAN.md` 참조
2. **시나리오 1 우선**: 현재 구현 대상은 시나리오 1(P1 입지 Top3 추천). 다른 시나리오 기능은 추가하지 않음
3. **단계별 진행**: 사용자가 "다음 단계 진행"을 요청할 때만 해당 단계 작업 수행
4. **문서 갱신 필수**: 작업 완료 시 반드시 아래 문서를 갱신:
   - `docs/PROGRESS.md` — 완료 티켓, 남은 티켓, 블로커, 다음 3개 액션
   - `docs/TODO.md` — 완료 체크, 새 티켓 추가
   - `docs/DECISIONS.md` — 새 결정사항 발생 시 추가
5. **다음 액션은 최대 3개만** 제시하고 멈춤
6. **UI 구현 시** 반드시 `docs/ui.md` 참고 — shadcn/ui 컴포넌트만 사용, date-fns 날짜 포맷

---

## 데이터베이스 스키마 (핵심)

### 차원 테이블
- `dim_area(area_id, area_type, area_code, area_name, geom)` — 행정동/상권 이원화
- `dim_category(cat_id, service_code, service_name)` — 업종 코드
- `preset_area_scope` — 성수동 프리셋 (행정동 4개 + 상권 20~40개)

### 팩트 테이블
- `fact_sales_area_qtr(area_id, qtr, cat_id, sales_amt, sales_cnt, confidence_score)`
- `fact_flow_area_qtr(area_id, qtr, flow_total, flow_by_hour, flow_by_weekday, flow_by_demo)`
- `fact_store_area_qtr(area_id, qtr, cat_id, store_cnt, open_cnt, close_cnt)`
- `fact_realtime_congestion_area(area_id, ts, congestion_level, ppltn_min, ppltn_max)`

### 브릿지/메타
- `bridge_area_h3_weight(area_id, h3_index, weight)` — 폴리곤→H3(res=9) 매핑
- `analysis_run(run_id, question, params_json, sql_text, result_json, assumptions_json, data_asof)`
- `ingest_runs`, `raw_objects`, `schema_registry` — 수집 메타

---

## 데이터셋 레퍼런스

| ID | 데이터 | 분류 | 키 |
|----|--------|------|-----|
| D1 | 추정매출(상권) | Must | 상권_코드 + 기준_년분기_코드 + 서비스_업종_코드 |
| D2 | 점포(행정동) | Must | 행정동_코드 + 기준_년분기_코드 + 서비스_업종_코드 |
| D3 | 상권영역(공간) | Must | 상권_코드 |
| D5 | 유동인구(상권) | Must | 상권_코드 + 기준_년분기_코드 |
| D9 | 행정동 경계(SHP) | Must | 행정동코드 |
| D11 | 실시간 도시데이터 | Should | AREA_CD + PPLTN_TIME |
| D4 | 상주인구(행정동) | Could | 행정동_코드 + 기준_년분기_코드 |
| D8 | 집객시설(상권배후지) | Could | 상권배후지_코드 + 기준_년분기_코드 |

---

## API 엔드포인트 (시나리오 1)

| 메서드 | 경로 | 용도 |
|--------|------|------|
| GET | `/api/map/hexagons?area_type=&category=&qtr=` | H3 그리드 + 집계값 |
| GET | `/api/map/hexagon/{h3_index}` | 특정 Hex 상세 (6개 카드) |
| GET | `/api/data/categories` | 업종 목록 |
| GET | `/api/data/area-scope` | 영역 프리셋 (행정동/상권) |
| POST | `/api/chat` | 챗봇 질의 (SSE 스트리밍) |

---

## AI 에이전트 (LangGraph)

```
User Query → Supervisor
               │
     ┌─────────┼─────────┐
     ▼                    ▼
SQL Agent           Insight Agent
(자연어→SQL)        (결과→근거/리스크/추천)
     │                    │
     └────────┬───────────┘
              ▼
         Response (data_asof 포함)
```

### 라우팅 규칙
- **SQL Agent**: "어디/언제/얼마/증가/감소/TopN/비교/분기/시간대" → SQL 생성+실행
- **Insight Agent**: "왜/추천/리스크/전략/~해도 될까" → 근거 구조화 (근거3 + 리스크2 + 추천2 + 체크리스트)
- 유튜브 OFF: Social Agent 비활성, Insight Agent가 공공데이터 근거 + "추가 확인 체크리스트" 제공

### SQL Agent 안전규칙
- SELECT만 허용. DDL/DML 금지
- 허용 테이블: dim_area, dim_category, fact_sales_area_qtr, fact_flow_area_qtr, fact_store_area_qtr, fact_realtime_congestion_area, bridge_area_h3_weight
- 기본 시간 범위: 최근 4개 분기. LIMIT 200 강제
- 성수동 필터: `preset_area_scope` 사용

---

## 개발 가이드라인

### 코드 스타일

**Python (Backend)**
- PEP 8 + ruff
- Type hints 필수
- Docstring: Google style
- 함수/클래스명: 명확하고 서술적으로

**TypeScript (Frontend)**
- ESLint + Prettier 설정 준수
- 컴포넌트: PascalCase
- 함수/변수: camelCase
- 타입 정의 필수

### 커밋 메시지
```
<type>(<scope>): <subject>

types: feat, fix, docs, style, refactor, test, chore
scope: frontend, backend, etl, docs
```

예시:
```
feat(frontend): Add HexagonMap component with Deck.gl
feat(backend): Add SQL agent for quantitative queries
fix(frontend): Fix hexagon click event handler
```

### 브랜치 전략
- `main`: 프로덕션
- `develop`: 개발
- `feature/*`: 기능 개발
- `fix/*`: 버그 수정

---

## 환경 변수

```bash
# Database
SUPABASE_URL=         # Supabase 프로젝트 URL
SUPABASE_KEY=         # Supabase anon/service key

# AI
OPENAI_API_KEY=       # OpenAI API 키

# External APIs
SEOUL_API_KEY=        # 서울 열린데이터 광장 API 키
MAPBOX_TOKEN=         # Mapbox 액세스 토큰

# App
NEXT_PUBLIC_API_URL=  # FastAPI 백엔드 URL

# 옵션
YOUTUBE_API_KEY=      # 유튜브 모듈 사용 시
GEMINI_API_KEY=       # 콘텐츠 생성(4컷/쇼츠) — Phase 4
```

### 로컬 개발

**Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

**Docker**
```bash
docker-compose up -d
```

---

## 주의사항

### 보안
- API 키 하드코딩 금지. `.env` 사용
- SQL Agent: parameterized query + 허용 테이블만 접근
- 사용자 입력 sanitize
- CORS 설정 필수

### 성능
- 맵 렌더링 < 3초
- 챗봇 응답 < 10초 (스트리밍 first token < 2초)
- H3 데이터 경량화 (GeoJSON 최소화)

### 데이터 후행성
- 공공데이터는 분기 후행(1~3개월). 모든 카드에 as-of 배지 필수
- "최근/요즘/오늘" 질의 시 D11 실시간 보정 카드 자동 동봉
- 단정 금지: "가능한 설명 + 추가 확인 체크리스트" 형태로 답변

---

## 마일스톤 현황

| 마일스톤 | 상태 | 내용 |
|---------|------|------|
| M0 Repo/Infra | 미시작 | 모노레포 + docker-compose + Next.js/FastAPI 스켈레톤 |
| M1 Data Layer | 미시작 | DDL + D1/D2/D3/D5/D9 적재 + H3 매핑 |
| M2 API Layer | 미시작 | Map/Data/Chat API + LangGraph 에이전트 |
| M3 UI Layer | 미시작 | 3D Hex맵 + 사이드바 + 챗봇 + 필터/토글 |
| M4 Eval/Logging | 미시작 | 골든 쿼리 + analysis_run + 이벤트 로그 |

상세: `docs/PLAN.md`, `docs/TODO.md`, `docs/PROGRESS.md`

---

## 참고 문서

- [PRD](K-CIA%20Lite.md) — 제품 요구사항
- [유저 시나리오](K-CIA_Lite_UserScenarios.md) — 8개 시나리오 상세 (6단계 + 데이터 설계)
- [데이터 기획](K-CIA_Lite_DataPlan.md) — 스키마/LLM 오케스트레이션/검증
- [데이터 수집 계획](K-CIA_Lite_DataIngestionPlan.md) — 수집 파이프라인/의사코드/메타 테이블
- [실행 계획](docs/PLAN.md) — 마일스톤/데이터 최소셋/확장 로드맵
- [의사결정 로그](docs/DECISIONS.md) — 확정된 결정사항과 근거
- [UI 코딩 표준](docs/ui.md) — **프론트엔드 구현 시 필수 참고** (shadcn/ui, date-fns)
