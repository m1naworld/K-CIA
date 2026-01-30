# K-CIA Lite: Technical Requirements Document (TRD)

**버전:** 1.1
**상태:** Draft
**작성일:** 2026-01-26
**최종 수정:** 2026-01-30

---

## 1. 문서 개요

이 문서는 K-CIA Lite의 기술 아키텍처, 시스템 설계, 구현 명세를 정의합니다.

---

## 2. 시스템 아키텍처

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Next.js Web Application                        │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │   │
│  │  │  Deck.gl 3D Map  │  │   Chat Interface │  │   Sidebar     │  │   │
│  │  │  + react-map-gl  │  │   (shadcn/ui)    │  │   (Filters)   │  │   │
│  │  └──────────────────┘  └──────────────────┘  └───────────────┘  │   │
│  │  ┌──────────────────┐  ┌──────────────────┐                     │   │
│  │  │  Recharts/Tremor │  │  Zustand/Jotai   │                     │   │
│  │  │  (Charts)        │  │  (State Mgmt)    │                     │   │
│  │  └──────────────────┘  └──────────────────┘                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              API Layer                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Server                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │   │
│  │  │  /api/blocks │  │ /api/agent   │  │  /api/data             │ │   │
│  │  │  헥사곤 데이터│  │  AI 질의     │  │  구역 상세 정보        │ │   │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           AI Orchestration Layer                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         LangGraph Engine                          │   │
│  │                                                                   │   │
│  │  ┌─────────────┐      ┌───────────────────────────────────────┐ │   │
│  │  │  Supervisor │─────▶│           Agent Pool                   │ │   │
│  │  │   Router    │      │  ┌─────────┐ ┌─────────┐ ┌─────────┐ │ │   │
│  │  └─────────────┘      │  │   SQL   │ │Sentiment│ │ Summary │ │ │   │
│  │                       │  │  Agent  │ │  Agent  │ │  Agent  │ │ │   │
│  │                       │  └─────────┘ └─────────┘ └─────────┘ │ │   │
│  │                       └───────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              Data Layer                                  │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐    │
│  │     Supabase PostgreSQL  │  │        Vector Store (pgvector)   │    │
│  │  ┌────────────────────┐  │  │  ┌────────────────────────────┐  │    │
│  │  │ sales_data         │  │  │  │ youtube_embeddings         │  │    │
│  │  │ floating_population│  │  │  │ sentiment_cache            │  │    │
│  │  │ hexagon_grid       │  │  │  └────────────────────────────┘  │    │
│  │  │ business_info      │  │  │                                  │    │
│  │  └────────────────────┘  │  │                                  │    │
│  └──────────────────────────┘  └──────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Data Collection Layer                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ETL Pipeline (Batch Jobs)                      │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │   │
│  │  │ Seoul Open Data  │  │  YouTube API     │  │  Sentiment    │  │   │
│  │  │ Collector        │  │  Collector       │  │  Processor    │  │   │
│  │  │ (분기별)          │  │  (일일)          │  │  (일일)        │  │   │
│  │  └──────────────────┘  └──────────────────┘  └───────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 기술 스택 상세

| 계층 | 기술 | 버전 | 용도 |
|-----|-----|-----|-----|
| **Frontend** | Next.js | 14+ (App Router) | React 기반 풀스택 프레임워크 |
| | Deck.gl | 9+ | WebGL 기반 3D 맵 시각화 |
| | react-map-gl | 7+ | Mapbox GL JS React 래퍼 |
| | TailwindCSS | 3+ | 유틸리티 퍼스트 CSS |
| | shadcn/ui | latest | 재사용 가능한 UI 컴포넌트 |
| | Recharts/Tremor | latest | 차트 시각화 |
| | Zustand/Jotai | latest | 경량 상태 관리 |
| | TypeScript | 5+ | 타입 안전성 |
| **Backend** | Python | 3.11+ | 메인 런타임 |
| | FastAPI | 0.109+ | REST API 서버 |
| | Uvicorn | 0.27+ | ASGI 서버 |
| | Pydantic | 2.6+ | 데이터 검증 |
| **AI/ML** | LangChain | 0.1+ | LLM 체인 구성 |
| | LangGraph | 0.1+ | 에이전트 워크플로우 |
| | OpenAI API | GPT-4o | LLM 추론 |
| | Sentence-Transformers | 2.3+ | 텍스트 임베딩 |
| **Database** | Supabase | - | BaaS (PostgreSQL) |
| | PostgreSQL | 15+ | 관계형 DB |
| | pgvector | 0.6+ | 벡터 유사도 검색 |
| **Infra** | Docker | 24+ | 컨테이너화 |
| | GitHub Actions | - | CI/CD |

---

## 3. 데이터베이스 설계

### 3.1 ERD (Entity Relationship Diagram)

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  hexagon_grid   │       │   sales_data    │       │floating_population│
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ PK hex_id       │───┐   │ PK id           │       │ PK id           │
│    h3_index     │   │   │ FK hex_id       │───────│ FK hex_id       │───┐
│    center_lat   │   │   │    year_quarter │       │    date         │   │
│    center_lng   │   │   │    industry_code│       │    hour         │   │
│    geometry     │   └───│    sales_amount │       │    population   │   │
│    district     │       │    store_count  │       │    age_group    │   │
│    updated_at   │       │    created_at   │       │    gender       │   │
└─────────────────┘       └─────────────────┘       └─────────────────┘
         │                                                   │
         │                                                   │
         ▼                                                   │
┌─────────────────┐       ┌─────────────────┐               │
│ youtube_videos  │       │youtube_comments │               │
├─────────────────┤       ├─────────────────┤               │
│ PK video_id     │───────│ PK comment_id   │               │
│    title        │       │ FK video_id     │               │
│    channel_name │       │    text         │               │
│    published_at │       │    author       │               │
│    view_count   │       │    published_at │               │
│    like_count   │       │    sentiment    │◄──────────────┘
│    description  │       │    embedding    │  (hex_id로 연결)
│    created_at   │       │    created_at   │
└─────────────────┘       └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│ sentiment_agg   │       │  business_info  │
├─────────────────┤       ├─────────────────┤
│ PK id           │       │ PK id           │
│ FK hex_id       │       │ FK hex_id       │
│    date         │       │    business_name│
│    avg_sentiment│       │    industry_code│
│    comment_count│       │    address      │
│    keywords     │       │    open_date    │
│    updated_at   │       │    close_date   │
└─────────────────┘       └─────────────────┘
```

### 3.2 테이블 스키마

#### 3.2.1 hexagon_grid
```sql
CREATE TABLE hexagon_grid (
    hex_id VARCHAR(20) PRIMARY KEY,      -- H3 인덱스 기반 ID
    h3_index VARCHAR(20) NOT NULL,       -- H3 라이브러리 인덱스
    center_lat DECIMAL(10, 7) NOT NULL,  -- 중심 위도
    center_lng DECIMAL(10, 7) NOT NULL,  -- 중심 경도
    geometry GEOMETRY(POLYGON, 4326),    -- 헥사곤 폴리곤
    district VARCHAR(50),                -- 행정구역 (성수1가 등)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_hexagon_h3 ON hexagon_grid(h3_index);
CREATE INDEX idx_hexagon_geo ON hexagon_grid USING GIST(geometry);
```

#### 3.2.2 sales_data
```sql
CREATE TABLE sales_data (
    id SERIAL PRIMARY KEY,
    hex_id VARCHAR(20) REFERENCES hexagon_grid(hex_id),
    year_quarter VARCHAR(7) NOT NULL,    -- '2025-Q4'
    industry_code VARCHAR(10) NOT NULL,  -- 업종코드
    industry_name VARCHAR(100),          -- 업종명
    sales_amount BIGINT,                 -- 추정 매출액 (원)
    store_count INTEGER,                 -- 점포 수
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(hex_id, year_quarter, industry_code)
);

CREATE INDEX idx_sales_hex ON sales_data(hex_id);
CREATE INDEX idx_sales_quarter ON sales_data(year_quarter);
```

#### 3.2.3 floating_population
```sql
CREATE TABLE floating_population (
    id SERIAL PRIMARY KEY,
    hex_id VARCHAR(20) REFERENCES hexagon_grid(hex_id),
    date DATE NOT NULL,
    hour INTEGER CHECK (hour >= 0 AND hour <= 23),
    population INTEGER NOT NULL,
    age_group VARCHAR(10),               -- '20-29', '30-39' 등
    gender VARCHAR(1),                   -- 'M', 'F'
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(hex_id, date, hour, age_group, gender)
);

CREATE INDEX idx_pop_hex ON floating_population(hex_id);
CREATE INDEX idx_pop_date ON floating_population(date);
```

#### 3.2.4 youtube_comments
```sql
CREATE TABLE youtube_comments (
    comment_id VARCHAR(50) PRIMARY KEY,
    video_id VARCHAR(20) REFERENCES youtube_videos(video_id),
    text TEXT NOT NULL,
    author VARCHAR(100),
    published_at TIMESTAMP,
    sentiment DECIMAL(3, 2),             -- -1.00 ~ 1.00
    hex_id VARCHAR(20),                  -- 연관된 헥사곤 (nullable)
    embedding VECTOR(384),               -- 문장 임베딩
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_comment_video ON youtube_comments(video_id);
CREATE INDEX idx_comment_sentiment ON youtube_comments(sentiment);
CREATE INDEX idx_comment_embedding ON youtube_comments
    USING ivfflat (embedding vector_cosine_ops);
```

#### 3.2.5 sentiment_agg (일별 감성 집계)
```sql
CREATE TABLE sentiment_agg (
    id SERIAL PRIMARY KEY,
    hex_id VARCHAR(20) REFERENCES hexagon_grid(hex_id),
    date DATE NOT NULL,
    avg_sentiment DECIMAL(4, 3),         -- 평균 감성 점수
    comment_count INTEGER,               -- 댓글 수
    positive_ratio DECIMAL(3, 2),        -- 긍정 비율
    keywords JSONB,                      -- 주요 키워드
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(hex_id, date)
);
```

---

## 4. API 설계

### 4.1 API 엔드포인트

#### 4.1.1 Blocks API (Map Data)

**GET /api/blocks**
```yaml
Description: 헥사곤 그리드 데이터 조회
Query Parameters:
  - layer: string (enum: population, sales, sentiment)
  - quarter: string (YYYY-Qn, optional)
  - industry: string (optional)
Response:
  - 200 OK
    {
      "hexagons": [
        {
          "hex_id": "8930624...",
          "center": [127.0456, 37.5443],
          "elevation": 150,
          "color": [120, 200, 80, 180],
          "metrics": {
            "population": 15234,
            "sales": 230000000,
            "sentiment": 0.72
          }
        }
      ],
      "bounds": {
        "min_lat": 37.53,
        "max_lat": 37.55,
        "min_lng": 127.03,
        "max_lng": 127.06
      }
    }
```

**GET /api/blocks/{hex_id}/summary**
```yaml
Description: 특정 헥사곤 상세 정보
Query Parameters:
  - quarter: string (YYYY-Qn)
  - industry: string (optional)
Response:
  - 200 OK
    {
      "hex_id": "8930624...",
      "district": "성수1가",
      "metrics": {
        "daily_population": 15234,
        "monthly_sales": 230000000,
        "sentiment_score": 0.72,
        "store_count": 45,
        "top_industries": [
          {"name": "카페", "ratio": 0.32},
          {"name": "음식점", "ratio": 0.25}
        ]
      },
      "recent_keywords": ["핫플", "브런치", "줄서서"],
      "trend": {
        "population_change": 0.12,
        "sentiment_change": 0.05
      }
    }
```

#### 4.1.2 Agent API (AI Chat)

**POST /api/agent/query**
```yaml
Description: AI 챗봇 질의
Request Body:
  {
    "question": "연무장길에 디저트 카페 차려도 될까?",
    "hex_id": "8930624...",
    "filters": {
      "quarter": "2025Q4",
      "industry": "cafe"
    },
    "recent_youtube_summary_ids": ["abc123", "def456"]
  }
Response:
  - 200 OK
    {
      "response": "분석 결과...",
      "sources": [
        {"type": "sales_data", "period": "2025-Q4"},
        {"type": "youtube", "count": 156}
      ],
      "suggested_questions": [
        "경쟁 카페 현황은?",
        "유동인구 시간대별 분석"
      ],
      "charts": [
        {"type": "bar", "data": {...}}
      ]
    }
```

**GET /api/agent/history/{session_id}**
```yaml
Description: 대화 히스토리 조회
Response:
  - 200 OK
    {
      "messages": [
        {"role": "user", "content": "...", "timestamp": "..."},
        {"role": "assistant", "content": "...", "timestamp": "..."}
      ]
    }
```

#### 4.1.3 Data API

**GET /api/data/industries**
```yaml
Description: 업종 코드 목록
Response:
  - 200 OK
    {
      "industries": [
        {"code": "Q01", "name": "커피음료"},
        {"code": "Q02", "name": "제과점"}
      ]
    }
```

**GET /api/data/trends**
```yaml
Description: 최근 트렌드 키워드
Query Parameters:
  - days: integer (default: 7)
Response:
  - 200 OK
    {
      "keywords": [
        {"word": "브런치", "count": 234, "sentiment": 0.8},
        {"word": "웨이팅", "count": 156, "sentiment": -0.3}
      ]
    }
```

### 4.2 에러 응답 형식
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid hex_id format",
    "details": {}
  }
}
```

---

## 5. LangGraph 에이전트 설계

### 5.1 워크플로우 다이어그램

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Supervisor │
                    │   Router    │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  SQL Agent  │ │  Sentiment  │ │   Summary   │
    │             │ │   Agent     │ │   Agent     │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Aggregator │
                    │    Node     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    END      │
                    └─────────────┘
```

### 5.2 에이전트 명세

#### 5.2.1 Supervisor Router
```python
class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    query_type: str  # 'quantitative', 'qualitative', 'hybrid'
    selected_agents: list[str]
    context: dict

def supervisor_router(state: SupervisorState) -> dict:
    """
    질문 유형을 분석하여 적절한 에이전트 선택

    분류 기준:
    - 정량적 질문 (매출, 인구, 점포 수) → SQL Agent
    - 정성적 질문 (반응, 트렌드, 분위기) → Sentiment Agent
    - 복합 질문 (창업 추천, 비교 분석) → Both + Summary
    """
```

#### 5.2.2 SQL Agent
```python
class SQLAgentState(TypedDict):
    query: str
    sql: str
    result: list[dict]
    error: str | None

SQL_AGENT_PROMPT = """
당신은 성수동 상권 데이터베이스 전문가입니다.
사용자 질문을 PostgreSQL 쿼리로 변환하세요.

사용 가능한 테이블:
- hexagon_grid: 헥사곤 그리드 정보
- sales_data: 매출 데이터 (year_quarter, industry_code, sales_amount)
- floating_population: 유동인구 (date, hour, population, age_group)
- business_info: 점포 정보

규칙:
1. 항상 hex_id로 조인
2. 최신 분기 데이터 우선 사용
3. 집계 시 NULL 처리
"""
```

#### 5.2.3 Sentiment Agent
```python
class SentimentAgentState(TypedDict):
    query: str
    hex_id: str | None
    comments: list[dict]
    summary: str
    keywords: list[str]

SENTIMENT_AGENT_PROMPT = """
당신은 성수동 소셜 미디어 분석가입니다.
유튜브 댓글을 분석하여 인사이트를 도출하세요.

분석 항목:
1. 전체 감성 점수 (-1 ~ 1)
2. 주요 긍정/부정 키워드
3. 자주 언급되는 장소/업종
4. 최근 트렌드 변화

출력 형식:
- 핵심 인사이트 3줄 요약
- 긍정/부정 요인 구분
- 관련 원문 댓글 인용 (2-3개)
"""
```

#### 5.2.4 Summary Agent
```python
SUMMARY_AGENT_PROMPT = """
당신은 상권 분석 컨설턴트입니다.
SQL 분석 결과와 감성 분석 결과를 종합하여 답변하세요.

답변 구조:
1. 핵심 결론 (1문장)
2. 긍정 요인 (bullet points)
3. 주의 요인 (bullet points)
4. 구체적 제안 (있다면)
5. 데이터 출처 명시

톤앤매너:
- 전문적이지만 이해하기 쉽게
- 숫자는 반드시 포함
- 불확실한 정보는 명시
"""
```

### 5.3 그래프 구성
```python
from langgraph.graph import StateGraph, END

def create_kcia_graph():
    workflow = StateGraph(KCIAState)

    # 노드 추가
    workflow.add_node("supervisor", supervisor_router)
    workflow.add_node("sql_agent", sql_agent)
    workflow.add_node("sentiment_agent", sentiment_agent)
    workflow.add_node("aggregator", aggregator_node)

    # 엣지 정의
    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_to_agents,
        {
            "sql_only": "sql_agent",
            "sentiment_only": "sentiment_agent",
            "both": "parallel_agents"
        }
    )

    workflow.add_edge("sql_agent", "aggregator")
    workflow.add_edge("sentiment_agent", "aggregator")
    workflow.add_edge("aggregator", END)

    return workflow.compile()
```

---

## 6. 데이터 파이프라인

### 6.1 ETL 프로세스

```
┌────────────────────────────────────────────────────────────────────┐
│                    Daily Pipeline (매일 02:00)                      │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│  │ YouTube  │───▶│  Extract │───▶│Transform │───▶│   Load   │    │
│  │   API    │    │ Comments │    │Sentiment │    │ Supabase │    │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                 Quarterly Pipeline (분기 첫째주)                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│  │Seoul API │───▶│ Extract  │───▶│Transform │───▶│   Load   │    │
│  │ (상권)   │    │Sales/Pop │    │ Normalize│    │ Supabase │    │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### 6.2 YouTube 수집 로직

```python
class YouTubeCollector:
    """
    성수동 관련 유튜브 영상 및 댓글 수집
    """

    SEARCH_KEYWORDS = [
        "성수동", "성수역", "서울숲", "연무장길",
        "성수 카페", "성수 맛집", "성수 핫플"
    ]

    async def collect_daily(self):
        """일일 수집 프로세스"""
        # 1. 키워드별 신규 영상 검색
        videos = await self.search_videos(
            keywords=self.SEARCH_KEYWORDS,
            published_after=datetime.now() - timedelta(days=1)
        )

        # 2. 영상별 댓글 수집
        for video in videos:
            comments = await self.get_comments(video.id, max_results=100)

            # 3. 감성 분석
            for comment in comments:
                comment.sentiment = self.analyze_sentiment(comment.text)
                comment.embedding = self.get_embedding(comment.text)

            # 4. 저장
            await self.save_to_db(video, comments)

        # 5. 일별 집계 업데이트
        await self.update_daily_aggregation()
```

### 6.3 서울시 공공데이터 수집

```python
class SeoulDataCollector:
    """
    서울시 공공데이터 포털 API 수집
    """

    APIS = {
        "sales": "서울시 상권분석서비스(추정매출)",
        "population": "서울시 생활인구",
        "business": "소상공인시장진흥공단_상가(상권)정보"
    }

    async def collect_quarterly(self):
        """분기별 수집 프로세스"""
        # 1. 성수동 행정동 코드로 필터링
        dong_codes = ["1120059", "1120060"]  # 성수1가, 성수2가

        # 2. 매출 데이터 수집
        sales_data = await self.fetch_sales_data(dong_codes)

        # 3. 유동인구 데이터 수집
        population_data = await self.fetch_population_data(dong_codes)

        # 4. 헥사곤 매핑
        hexagon_data = self.map_to_hexagons(sales_data, population_data)

        # 5. 저장
        await self.upsert_to_db(hexagon_data)
```

---

## 7. 프론트엔드 구현

### 7.1 Next.js 앱 구조

```
frontend/
├── app/                       # Next.js App Router
│   ├── layout.tsx            # 루트 레이아웃
│   ├── page.tsx              # 메인 페이지 (지도 대시보드)
│   ├── globals.css           # 전역 스타일 (Tailwind)
│   └── api/                  # API Routes (필요시)
├── components/
│   ├── ui/                   # shadcn/ui 컴포넌트
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   └── ...
│   ├── map/
│   │   ├── HexagonMap.tsx    # Deck.gl 맵 컴포넌트
│   │   ├── MapControls.tsx   # 줌/레이어 컨트롤
│   │   └── HexagonTooltip.tsx
│   ├── chat/
│   │   ├── ChatInterface.tsx # AI 챗봇 UI
│   │   ├── ChatMessage.tsx
│   │   └── ChatInput.tsx
│   ├── sidebar/
│   │   ├── FilterPanel.tsx   # 필터 패널
│   │   ├── HexagonDetail.tsx # 선택 구역 상세
│   │   └── MetricCard.tsx
│   └── charts/
│       ├── SalesChart.tsx    # Recharts 매출 차트
│       ├── TrendChart.tsx
│       └── CompareChart.tsx
├── lib/
│   ├── api.ts                # FastAPI 클라이언트
│   ├── utils.ts              # 유틸리티 함수
│   └── constants.ts          # 상수 정의
├── stores/
│   └── useMapStore.ts        # Zustand 상태 관리
├── types/
│   └── index.ts              # TypeScript 타입 정의
├── tailwind.config.ts
├── next.config.js
└── package.json
```

### 7.2 Deck.gl 3D 맵 구성

```tsx
// components/map/HexagonMap.tsx
import { DeckGL } from '@deck.gl/react';
import { H3HexagonLayer } from '@deck.gl/geo-layers';
import { Map } from 'react-map-gl';
import { useMapStore } from '@/stores/useMapStore';

interface HexagonData {
  hex_id: string;
  elevation: number;
  color: [number, number, number, number];
  metrics: {
    population: number;
    sales: number;
    sentiment: number;
  };
}

export function HexagonMap() {
  const { hexagons, selectedHexId, setSelectedHexId } = useMapStore();

  const layer = new H3HexagonLayer<HexagonData>({
    id: 'h3-hexagon-layer',
    data: hexagons,
    pickable: true,
    wireframe: false,
    filled: true,
    extruded: true,
    elevationScale: 50,
    getHexagon: (d) => d.hex_id,
    getFillColor: (d) => d.color,
    getElevation: (d) => d.elevation,
    onClick: (info) => {
      if (info.object) {
        setSelectedHexId(info.object.hex_id);
      }
    },
  });

  return (
    <DeckGL
      initialViewState={{
        latitude: 37.5443,
        longitude: 127.0557,
        zoom: 14,
        pitch: 45,
        bearing: 0,
      }}
      controller={true}
      layers={[layer]}
    >
      <Map
        mapStyle="mapbox://styles/mapbox/dark-v11"
        mapboxAccessToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
      />
    </DeckGL>
  );
}
```

### 7.3 상태 관리 (Zustand)

```typescript
// stores/useMapStore.ts
import { create } from 'zustand';
import type { HexagonData, Filters } from '@/types';

interface MapState {
  hexagons: HexagonData[];
  selectedHexId: string | null;
  filters: Filters;
  isLoading: boolean;

  // Actions
  setHexagons: (hexagons: HexagonData[]) => void;
  setSelectedHexId: (hexId: string | null) => void;
  setFilters: (filters: Partial<Filters>) => void;
  fetchHexagons: () => Promise<void>;
}

export const useMapStore = create<MapState>((set, get) => ({
  hexagons: [],
  selectedHexId: null,
  filters: {
    quarter: '2025Q4',
    industry: null,
    layer: 'population',
  },
  isLoading: false,

  setHexagons: (hexagons) => set({ hexagons }),
  setSelectedHexId: (hexId) => set({ selectedHexId: hexId }),
  setFilters: (filters) => set((state) => ({
    filters: { ...state.filters, ...filters }
  })),

  fetchHexagons: async () => {
    set({ isLoading: true });
    const { filters } = get();
    const response = await fetch(`/api/blocks?${new URLSearchParams(filters)}`);
    const data = await response.json();
    set({ hexagons: data.hexagons, isLoading: false });
  },
}));
```

### 7.4 Chat Interface

```tsx
// components/chat/ChatInterface.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { ChatMessage } from './ChatMessage';
import { useMapStore } from '@/stores/useMapStore';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: { type: string; period?: string; count?: number }[];
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { selectedHexId, filters } = useMapStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const response = await fetch('/api/agent/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: input,
        hex_id: selectedHexId,
        filters,
      }),
    });

    const data = await response.json();
    const assistantMessage: Message = {
      role: 'assistant',
      content: data.response,
      sources: data.sources,
    };

    setMessages((prev) => [...prev, assistantMessage]);
    setIsLoading(false);
  };

  return (
    <Card className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {isLoading && <div className="text-muted-foreground">분석 중...</div>}
      </div>
      <form onSubmit={handleSubmit} className="p-4 border-t flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="질문을 입력하세요..."
          disabled={isLoading}
        />
        <Button type="submit" disabled={isLoading}>
          전송
        </Button>
      </form>
    </Card>
  );
}
```

---

## 8. 배포 및 인프라

### 8.1 Docker 구성

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
      - NEXT_PUBLIC_MAPBOX_TOKEN=${MAPBOX_TOKEN}
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - YOUTUBE_API_KEY=${YOUTUBE_API_KEY}

  worker:
    build: ./backend
    command: python -m celery -A worker worker -l info
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
```

### 8.2 환경 변수

```bash
# .env.example

# Database
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...

# AI
OPENAI_API_KEY=sk-...

# External APIs
YOUTUBE_API_KEY=AIza...
SEOUL_API_KEY=...
MAPBOX_TOKEN=pk.eyJ...

# App
DEBUG=false
LOG_LEVEL=INFO
```

### 8.3 CI/CD 파이프라인

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run build

  deploy:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Vercel (Frontend)
        uses: vercel/action@v1
        with:
          working-directory: frontend
      - name: Deploy to Railway/Render (Backend)
        # Backend deployment steps
```

---

## 9. 모니터링 및 로깅

### 9.1 로깅 전략

```python
import logging
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# 로그 예시
logger.info("Chat query processed", extra={
    "session_id": session_id,
    "query_type": "hybrid",
    "response_time_ms": 2500,
    "tokens_used": 1500
})
```

### 9.2 메트릭 수집

| 메트릭 | 설명 | 알림 임계값 |
|-------|-----|-----------|
| `api_latency_p95` | API 응답 시간 95 퍼센타일 | > 5초 |
| `chat_error_rate` | 챗봇 에러율 | > 5% |
| `etl_success_rate` | ETL 파이프라인 성공률 | < 95% |
| `db_connection_pool` | DB 커넥션 풀 사용량 | > 80% |

---

## 10. 보안 고려사항

### 10.1 보안 체크리스트

- [ ] 모든 API 키 환경 변수로 관리
- [ ] SQL 인젝션 방지 (parameterized queries)
- [ ] XSS 방지 (사용자 입력 sanitize)
- [ ] Rate limiting 적용
- [ ] HTTPS 강제
- [ ] 민감 데이터 로깅 금지
- [ ] CORS 설정 (허용된 origin만)

### 10.2 SQL 인젝션 방지

```python
# ❌ 취약한 코드
query = f"SELECT * FROM sales WHERE hex_id = '{hex_id}'"

# ✅ 안전한 코드
query = "SELECT * FROM sales WHERE hex_id = %s"
cursor.execute(query, (hex_id,))
```

---

## 11. 테스트 전략

### 11.1 테스트 범위

| 유형 | 대상 | 도구 |
|-----|-----|-----|
| Unit | 유틸리티 함수, 데이터 변환 | pytest, vitest |
| Integration | API 엔드포인트, DB 쿼리 | pytest + httpx |
| E2E | 사용자 시나리오 | Playwright |
| Load | 동시 접속, 응답 시간 | Locust |

### 11.2 테스트 예시

```python
# backend/tests/test_agents.py
import pytest
from agents.sql_agent import SQLAgent

@pytest.mark.asyncio
async def test_sql_agent_simple_query():
    agent = SQLAgent()
    result = await agent.process("연무장길 카페 수는?")

    assert result.sql is not None
    assert "SELECT" in result.sql
    assert "cafe" in result.sql.lower() or "커피" in result.sql

@pytest.mark.asyncio
async def test_sql_agent_invalid_query():
    agent = SQLAgent()
    result = await agent.process("오늘 날씨 어때?")

    assert result.error is not None
    assert "상권" in result.error or "지원하지 않" in result.error
```

```typescript
// frontend/__tests__/HexagonMap.test.tsx
import { render, screen } from '@testing-library/react';
import { HexagonMap } from '@/components/map/HexagonMap';

describe('HexagonMap', () => {
  it('renders map container', () => {
    render(<HexagonMap />);
    expect(screen.getByTestId('deck-gl-canvas')).toBeInTheDocument();
  });
});
```

---

## 12. 부록

### 12.1 H3 인덱스 해상도

| Resolution | Avg Edge Length | Use Case |
|-----------|-----------------|----------|
| 9 | 174m | 구역 단위 |
| 10 | 66m | 블록 단위 |
| **11** | **25m** | **K-CIA 기본값** |
| 12 | 9m | 건물 단위 |

### 12.2 감성 점수 기준

| 점수 범위 | 분류 | 색상 (RGB) |
|----------|-----|-----------|
| 0.6 ~ 1.0 | 매우 긍정 | (0, 200, 0) |
| 0.2 ~ 0.6 | 긍정 | (100, 200, 100) |
| -0.2 ~ 0.2 | 중립 | (200, 200, 100) |
| -0.6 ~ -0.2 | 부정 | (200, 100, 100) |
| -1.0 ~ -0.6 | 매우 부정 | (200, 0, 0) |

---

*Document Owner: Engineering Team*
*Last Updated: 2026-01-30*
