# K-CIA Lite

성수동 하이퍼로컬 상권 분석 AI 플랫폼

> "성수동의 어제와 오늘을 3D 지도와 대화로 읽어주는 AI 컨설턴트"

## 핵심 기능

- **3D Hex 맵**: H3(res=9) 기반 헥사곤 그리드 — 높이(유동/매출), 색상(증감률)
- **AI 챗봇**: LangGraph 멀티에이전트 — 자연어 질의 → 데이터 근거 추천/리스크/체크리스트
- **공공데이터 기반**: 서울시 매출/유동인구/점포 + 실시간 보정(D11)
- **행정동/상권 토글**: 두 가지 영역 기준을 동시 지원

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Next.js 14 (App Router), Deck.gl, TailwindCSS, shadcn/ui |
| Backend | Python 3.11+, FastAPI, LangGraph, LangChain |
| AI | OpenAI GPT-4o, Vercel AI SDK |
| Database | Supabase (PostgreSQL + PostGIS + pgvector) |
| State | Zustand |

## 프로젝트 구조

```
K-CIA/
├── docs/               # 프로젝트 문서
│   ├── PLAN.md          # 실행 계획서
│   ├── TODO.md          # 작업 티켓
│   ├── PROGRESS.md      # 진행상황 로그
│   └── DECISIONS.md     # 의사결정 로그
├── frontend/            # Next.js 앱 (구현 예정)
├── backend/             # FastAPI 서버 (구현 예정)
├── etl/                 # 데이터 파이프라인 (구현 예정)
└── tests/               # 테스트
```

## 문서

- [PRD](K-CIA%20Lite.md) — 제품 요구사항
- [유저 시나리오](K-CIA_Lite_UserScenarios.md) — 8개 시나리오 상세
- [데이터 기획](K-CIA_Lite_DataPlan.md) — 데이터 소스/스키마/LLM 설계
- [데이터 수집 계획](K-CIA_Lite_DataIngestionPlan.md) — 수집 파이프라인 상세
- [실행 계획](docs/PLAN.md) — 마일스톤/데이터 최소셋/확장 로드맵

## 현재 상태

**Phase: Planning Complete** — 시나리오 1(P1 입지 Top3 추천) 중심 실행 계획 수립 완료. 코드 구현 대기 중.
