# CLAUDE.md - K-CIA Lite Project Guide

이 파일은 AI 어시스턴트(Claude)가 K-CIA Lite 프로젝트를 이해하고 효과적으로 지원하기 위한 컨텍스트를 제공합니다.

---

## 프로젝트 개요

**K-CIA Lite**는 성수동 하이퍼로컬 상권 분석 AI 플랫폼입니다.

- **핵심 가치**: 공공데이터(정량)와 소셜 트렌드(정성)를 결합한 인사이트 제공
- **타겟 사용자**: 예비 창업자, 부동산/마케팅 전문가
- **한 줄 정의**: "성수동의 어제와 오늘을 3D 지도와 대화로 읽어주는 AI 컨설턴트"

---

## 기술 스택

### Frontend
| 기술 | 용도 |
|-----|-----|
| Next.js (App Router) | React 기반 풀스택 프레임워크 |
| Deck.gl + react-map-gl | WebGL 기반 3D 지도 시각화 |
| TailwindCSS | 유틸리티 퍼스트 CSS |
| shadcn/ui | 재사용 가능한 UI 컴포넌트 |
| Recharts / Tremor | 차트 시각화 |
| Zustand / Jotai | 경량 상태 관리 |
| TypeScript | 타입 안전성 |

### Backend
| 기술 | 용도 |
|-----|-----|
| Python 3.11+ | 메인 런타임 |
| FastAPI | REST API 서버 |
| LangChain + LangGraph | LLM 오케스트레이션 |
| OpenAI GPT-4o | LLM 추론 |

### Database & Infra
| 기술 | 용도 |
|-----|-----|
| Supabase (PostgreSQL + pgvector) | 관계형 DB + 벡터 검색 |
| Docker | 컨테이너화 |
| GitHub Actions | CI/CD |

### Data Sources
- 서울시 공공데이터 API
- YouTube Data API

---

## 프로젝트 구조

```
K-CIA/
├── CLAUDE.md              # AI 어시스턴트 가이드 (현재 파일)
├── K-CIA Lite.md          # 초기 기획서
├── docs/
│   ├── PRD.md             # Product Requirements Document
│   └── TRD.md             # Technical Requirements Document
├── frontend/              # Next.js 앱 (구현 예정)
│   ├── app/               # App Router 페이지
│   ├── components/        # React 컴포넌트
│   │   ├── ui/           # shadcn/ui 컴포넌트
│   │   ├── map/          # Deck.gl 맵 컴포넌트
│   │   ├── chat/         # 챗봇 UI
│   │   ├── sidebar/      # 필터/상세 패널
│   │   └── charts/       # Recharts 차트
│   ├── lib/              # 유틸리티
│   ├── stores/           # Zustand 스토어
│   └── types/            # TypeScript 타입
├── backend/               # FastAPI 서버 (구현 예정)
│   ├── api/
│   ├── agents/
│   └── services/
├── etl/                   # 데이터 파이프라인 (구현 예정)
│   ├── collectors/
│   └── processors/
├── tests/                 # 테스트 코드
├── docker-compose.yml
└── .env.example
```

---

## 핵심 기능

### 1. 3D 헥사곤 맵 (FR-1)
- 성수동을 H3 헥사곤 그리드로 분할
- Elevation: 유동인구/매출 반영
- Color: 감성 점수(-1~1) 반영
- Deck.gl H3HexagonLayer 사용

### 2. AI 챗봇 (FR-2)
- LangGraph 기반 멀티 에이전트 시스템
- Supervisor: 질문 유형 라우팅
- SQL Agent: 정량 데이터 쿼리
- Sentiment Agent: 감성 분석 요약
- Summary Agent: 결과 종합

### 3. 데이터 수집 엔진 (FR-3)
- 서울시 API: 분기별 매출/유동인구
- YouTube API: 일일 댓글/트렌드
- 감성 분석 파이프라인

---

## 개발 가이드라인

### 코드 스타일

**Python (Backend)**
- PEP 8 준수
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
docs: Update TRD with API specifications
```

### 브랜치 전략
- `main`: 프로덕션 브랜치
- `develop`: 개발 브랜치
- `feature/*`: 기능 개발
- `fix/*`: 버그 수정
- `docs/*`: 문서 작업

---

## 환경 설정

### 필수 환경 변수
```bash
# Database
SUPABASE_URL=         # Supabase 프로젝트 URL
SUPABASE_KEY=         # Supabase anon/service key

# AI
OPENAI_API_KEY=       # OpenAI API 키

# External APIs
YOUTUBE_API_KEY=      # YouTube Data API 키
SEOUL_API_KEY=        # 서울 열린데이터 광장 API 키
MAPBOX_TOKEN=         # Mapbox 액세스 토큰

# App
NEXT_PUBLIC_API_URL=  # FastAPI 백엔드 URL
```

### 로컬 개발 실행

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

## 데이터베이스 스키마

### 핵심 테이블
- `hexagon_grid`: H3 인덱스 기반 그리드 정보
- `sales_data`: 분기별 업종별 매출 데이터
- `floating_population`: 시간대별 유동인구
- `youtube_comments`: 댓글 + 감성 점수 + 임베딩
- `sentiment_agg`: 일별 감성 집계

### H3 해상도
- Resolution 11 사용 (약 25m edge)
- 성수동 전체 약 500-600개 헥사곤

---

## API 엔드포인트

### Blocks API (Map)
- `GET /api/blocks` - 헥사곤 그리드 조회
- `GET /api/blocks/{hex_id}/summary` - 특정 헥사곤 상세

### Agent API (Chat)
- `POST /api/agent/query` - AI 챗봇 질의
- `GET /api/agent/history/{session_id}` - 대화 히스토리

### Data API
- `GET /api/data/industries` - 업종 목록
- `GET /api/data/trends` - 트렌드 키워드

---

## AI 에이전트 워크플로우

```
User Query → Supervisor Router
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
SQL Agent  Sentiment    Summary
    │       Agent          │
    └───────────┬──────────┘
                ▼
           Aggregator → Response
```

### 질의 유형 분류
1. **정량**: "매출", "인구", "점포 수" → SQL Agent
2. **정성**: "반응", "트렌드", "분위기" → Sentiment Agent
3. **복합**: "~해도 될까?", "비교 분석" → Multi-Agent

---

## 주의사항

### 보안
- API 키는 절대 코드에 하드코딩 금지
- 사용자 입력은 항상 sanitize
- SQL은 parameterized query 사용
- CORS 설정 필수

### 성능
- 맵 렌더링 < 2초 목표
- 챗봇 응답 < 10초 목표
- 동시 사용자 100명 지원

### 데이터
- 공공데이터는 3개월 지연됨을 인지
- 감성 분석은 완벽하지 않음을 사용자에게 명시
- 출처 항상 표시

---

## 다음 구현 단계

### Phase 1: 기반 구축
- [ ] Supabase 프로젝트 설정
- [ ] 테이블 스키마 생성
- [ ] H3 헥사곤 그리드 초기화

### Phase 2: 데이터 수집
- [ ] 서울시 API 연동
- [ ] YouTube API 연동
- [ ] 감성 분석 파이프라인

### Phase 3: 백엔드
- [ ] FastAPI 서버 구축
- [ ] LangGraph 에이전트 구현
- [ ] API 엔드포인트 개발

### Phase 4: 프론트엔드
- [ ] Next.js 프로젝트 초기화
- [ ] Deck.gl 3D 맵 구현
- [ ] shadcn/ui 기반 UI 개발
- [ ] Zustand 상태 관리 설정
- [ ] 챗봇 UI 개발

### Phase 5: 통합 및 배포
- [ ] 컴포넌트 통합
- [ ] 테스트 작성
- [ ] Docker 배포
- [ ] Vercel (Frontend) + Railway/Render (Backend) 배포

---

## 참고 문서

- [PRD.md](docs/PRD.md) - 제품 요구사항 상세
- [TRD.md](docs/TRD.md) - 기술 요구사항 상세
- [K-CIA Lite.md](K-CIA%20Lite.md) - 초기 기획서

---

## 문의

프로젝트 관련 질문이나 기여는 GitHub Issues를 통해 제출해주세요.
