# K-CIA Lite 환경 설정 가이드

## 1. .env 파일 생성

```bash
cd /Users/sungwoon/ai-projects/K-CIA
cp .env.example .env
```

---

## 2. 필수 API 키 발급

### (1) OPENAI_API_KEY (필수)

**용도:** 챗봇 AI 응답 (SQL Agent, Insight Agent)

**발급 방법:**
1. https://platform.openai.com 접속
2. 로그인 (계정 없으면 가입)
3. 우측 상단 프로필 → **API keys** 클릭
4. **Create new secret key** 클릭
5. 이름 입력 (예: "K-CIA") → **Create secret key**
6. 키 복사 (한 번만 표시됨!)

```bash
# .env에 추가
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
```

**비용:** GPT-4o-mini 기준 $0.15/1M input tokens

---

### (2) SEOUL_API_KEY (필수)

**용도:** 서울시 공공데이터 (매출, 유동인구, 점포, 실시간 혼잡도)

**발급 방법:**
1. https://data.seoul.go.kr 접속
2. 회원가입 및 로그인
3. 우측 상단 **마이페이지** → **인증키 신청**
4. 이용목적: "상권분석 서비스 개발"
5. 신청 후 즉시 발급됨 (메일 확인)

```bash
# .env에 추가
SEOUL_API_KEY=7a6b5c4d3e2f1g0h...
```

**무료:** 일 1,000회 호출

---

### (3) MAPBOX_TOKEN (선택 - 지도 타일)

**용도:** 고품질 지도 타일 (현재는 CARTO 무료 타일 사용 중)

**발급 방법:**
1. https://www.mapbox.com 접속
2. **Sign up** → 계정 생성
3. 로그인 후 **Account** → **Tokens**
4. **Default public token** 복사 또는 새 토큰 생성

```bash
# .env에 추가 (선택)
MAPBOX_TOKEN=pk.eyJ1Ijoixxxxxxxxxx
NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1Ijoixxxxxxxxxx
```

**무료:** 월 50,000 맵 로드

---

## 3. 선택적 API 키

### (4) SEMAS_API_KEY (M5 점포 weight용)

**용도:** 소상공인시장진흥공단 점포 좌표 데이터

**발급 방법:**
1. https://www.data.go.kr 접속
2. "소상공인시장진흥공단_상가(상권)정보" 검색
3. **활용신청** 클릭
4. 승인 후 마이페이지에서 키 확인 (1-2일 소요)

```bash
SEMAS_API_KEY=xxxxxxxxxxxxxxxx
```

---

### (5) SUPABASE (프로덕션 배포용)

**용도:** 클라우드 PostgreSQL (로컬 개발 시 불필요)

**발급 방법:**
1. https://supabase.com 접속
2. **Start your project** → GitHub 로그인
3. **New project** 생성
4. **Settings** → **API** → URL과 anon key 복사

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...
```

---

## 4. 최종 .env 파일 예시

```bash
# Database (로컬 Docker)
POSTGRES_USER=kcia
POSTGRES_PASSWORD=kcia_local_pw
POSTGRES_DB=kcia
DATABASE_URL=postgresql://kcia:kcia_local_pw@db:5432/kcia

# AI (필수)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx

# 서울시 공공데이터 (필수)
SEOUL_API_KEY=7a6b5c4d3e2f1g0h...

# 지도 (선택)
MAPBOX_TOKEN=pk.eyJ1Ijoixxxxxxxxxx
NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1Ijoixxxxxxxxxx

# App
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 5. 실행 방법

### Step 1: Docker 실행
```bash
cd /Users/sungwoon/ai-projects/K-CIA
docker compose up -d
```

### Step 2: DB 마이그레이션
```bash
# 컨테이너 접속
docker compose exec db psql -U kcia -d kcia

# SQL 실행 (psql 내에서)
\i /workspace/backend/migrations/001_init_schema.sql
\q
```

### Step 3: 데이터 적재
```bash
# 경계 데이터 (D3, D9)
docker compose run --rm --entrypoint python etl -m etl.load_boundaries

# H3 매핑
docker compose run --rm --entrypoint python etl -m etl.load_h3

# 매출 데이터 (D1)
docker compose run --rm --entrypoint python etl -m etl.load_sales_api 20251

# 유동인구 (D5)
docker compose run --rm --entrypoint python etl -m etl.load_flow_api 20244

# 점포 (D2)
docker compose run --rm --entrypoint python etl -m etl.load_store_api
```

### Step 4: 서비스 접속
- **프론트엔드:** http://localhost:3000
- **백엔드 API:** http://localhost:8000
- **API 문서:** http://localhost:8000/docs

---

## 6. 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| 챗봇 응답 없음 | OPENAI_API_KEY 미설정 | .env 확인 |
| 데이터 적재 실패 | SEOUL_API_KEY 미설정 | 키 발급 후 재시도 |
| 지도 안 보임 | MAPBOX_TOKEN 미설정 | CARTO 타일로 대체됨 (정상) |
| DB 연결 실패 | Docker 미실행 | `docker compose up -d` |

---

## 7. 데이터 소스 원본 링크

| 데이터 | 링크 |
|--------|------|
| D1 추정매출 | https://data.seoul.go.kr/dataList/OA-15572/S/1/datasetView.do |
| D2 점포 | https://data.seoul.go.kr/dataList/OA-22172/S/1/datasetView.do |
| D3 상권영역 | https://data.seoul.go.kr/dataList/OA-15560/S/1/datasetView.do |
| D5 유동인구 | https://www.data.go.kr/data/15094719/fileData.do |
| D9 행정동경계 | https://www.data.go.kr/data/15125055/fileData.do |
| D11 실시간 | https://data.seoul.go.kr/dataList/OA-21285/A/1/datasetView.do |
