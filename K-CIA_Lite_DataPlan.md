# K-CIA_Lite_DataPlan

# K-CIA Lite — 데이터 기획문서 (공공데이터 중심)

작성일: 2026-01-30

> 본 문서는 데이터 소스/스키마/파이프라인/LLM 오케스트레이션/검증에 집중합니다. 유저 시나리오는 별도 문서로 분리합니다.
> 

## 3) 공공데이터 핵심 카탈로그(시나리오에서 참조)

> 핵심 조인 키/공간 키 중심으로 정리했습니다.
> 
> 
> **결정(Q1)**: 성수동 범위는 **행정동 기준 + 상권코드 기준을 둘 다 지원**합니다.
> 
> - UI에서 `영역 기준(행정동/상권)` 토글 제공
> 
> - 저장/집계는 `dim_area(area_type)`로 분리하고, 필요 시 공간조인으로 상호 매핑(양방향)
> 
> - 기본 프리셋은 **행정동(성수1가1동/성수1가2동/성수2가1동/성수2가3동)** ∪ **골목상권(연무장길/성수역/뚝섬역 주변 상권코드)** 형태로 제공
> 

### 3.1 필수 1순위 (수요/경쟁/공간)

- **D1 추정매출(상권)**: 서울시 상권분석서비스(추정매출-상권)
    - 링크: https://data.seoul.go.kr/dataList/OA-15572/F/1/datasetView.do
    - 키: `기준_년분기_코드`, `상권_코드`, `서비스_업종_코드`
- **D2 점포(행정동)**: 서울시 상권분석서비스(점포-행정동)
    - 링크: https://data.seoul.go.kr/dataList/OA-22172/S/1/datasetView.do
    - 키: `기준_년분기_코드`, `행정동_코드`, `서비스_업종_코드`
- **D3 상권영역(공간)**: 상권분석서비스(영역-상권) *(좌표계 EPSG:5181)*
    - 링크: https://data.seoul.go.kr/dataList/OA-15560/S/1/datasetView.do
    - 키: `상권_코드`, (공간정보)
- **D5 생활/유동인구(상권)**: 우리마을가게 상권분석서비스(상권-생활인구/길단위인구-상권)
    - 링크: https://www.data.go.kr/data/15094719/fileData.do?recommendDataYn=Y
    - 키: `기준_년분기_코드`, `상권_코드` (+ 시간대/요일/성별/연령대 등)
- **D9 행정동 경계(SHP)**: 국토교통부 센서스 행정동 경계
    - 링크: https://www.data.go.kr/data/15125055/fileData.do?recommendDataYn=Y
    - 키: 행정동 코드(속성), 폴리곤(공간)

### 3.2 보조 2순위 (설명력/보정용)

- **D11 서울시 실시간 도시데이터(즉시성 보정 핵심)**: 서울시 실시간 도시데이터(주요 120장소)
    - 링크: https://data.seoul.go.kr/dataList/OA-21285/A/1/datasetView.do
    - 특징: 분/시간 단위의 **현황성 신호(혼잡도 등)** 제공. 과거 분석이 필요하면 **우리 DB에 스냅샷 적재**(예: 5~10분 간격) 권장
    - 키: `AREA_NM`(장소명) 또는 `AREA_CD`(장소코드), `PPLTN_TIME`(관측시각) 등
- **D4 상주인구(행정동)**: 상권분석서비스(상주인구-행정동)
    - 링크: https://data.seoul.go.kr/dataList/OA-22183/S/1/datasetView.do
    - 키: `기준_년분기_코드`, `행정동_코드`
- **D8 집객시설(상권배후지)**: 상권분석서비스(집객시설-상권배후지)
    - 링크: https://data.seoul.go.kr/dataList/OA-15581/S/1/datasetView.do
    - 키: `기준_년분기_코드`, `상권배후지_코드`
- **D10 임대(대체 지표)**: 서울교통공사 지하상가임대정보(월임대료 등)
    - 링크: https://data.seoul.go.kr/dataList/OA-12927/F/1/datasetView.do
    - 키: 역/상가 단위(상권과는 공간 조인으로 연결)

### 3.3 투자/임대 보강(공공·통계 기반, 거시/대체)

- **D14 상업업무용 부동산 매매 실거래가(OpenAPI)**: 국토교통부(법정동 코드 + 계약년월 기반 조회)
    - 링크: https://www.data.go.kr/data/15126463/openapi.do
    - 키: `법정동코드(앞5자리)`, `계약년월(YYYYMM)`, `거래금액`, `전용면적`, `층`, `건축년도` 등
    - 메모: 성수동 “미시”까지 완전 커버는 어려울 수 있어 **법정동/기간 필터 + 공간보정(좌표/주소 매핑)** 필요
- **D15 매장용빌딩 임대료·공실률 및 수익률(분기 통계)**: 서울시 통계(거시 리스크/수익률 보정)
    - 링크: https://data.seoul.go.kr/dataList/OA-12553/S/1/datasetView.do
    - 키: `기준_년분기`, `지역`, `임대료`, `공실률`, `수익률` 등
    - 메모: 성수동 단위로 내려오지 않을 수 있어 “거시 레퍼런스(리스크 배지)”로 사용

---

---

## (옵션) 유튜브/소셜 데이터 모듈 설계 (공공데이터 1순위 유지)

> 목적: 공공데이터(분기/월) 후행을 보정하고, “왜(맥락)” 설명력을 강화한다.
> 
> 
> 원칙: 유튜브 모듈은 **옵션**이며, OFF 상태에서도 Q&A/추천이 완결되어야 한다.
> 

### Y1) 소스/수집 단위

- **YouTube Data API v3**: 검색(키워드), 영상 메타데이터, 댓글(또는 일부) 수집
- **수집 주기**: 1일 1회(기본) + 선택(6시간 단위)
- **스코프**: 기본은 “성수동 범위(지역 스코프)” 레벨 집계
    - 고도화: 장소/POI 단서(지오태그·장소명·텍스트 언급)를 이용해 **H3 매핑** 시도

### Y2) 핵심 필드(최소)

- video: `video_id`, `channel_id`, `title`, `description`, `published_at`, `view_count`, `like_count`, `comment_count`
- comment: `comment_id`, `video_id`, `author`, `published_at`, `text_original`, `like_count`
- derived: `sentiment_score(-1~1)`, `buzz_volume`, `topic_keywords`, `summary_text`, `scope_level(Seongsu/H3)`

### Y3) 공간 매핑(조인 방향)

- **기본(안전)**: `scope=성수동`(행정동/상권코드 집합)로만 귀속 → 지도는 “범위 스코프 카드”로 표시
- **고도화(가능 시)**:
    1. 지오태그/위치 메타 → 좌표 → H3
    2. 텍스트에서 POI·역명·거리 NER → POI 테이블 매칭 → 좌표 → H3
    3. 불확실하면 “H3 미귀속(스코프만)”로 남겨 오표기 방지

### Y4) 집계 로직(일 단위)

- `fact_youtube_trend_day_scope(day × scope_id)`
    - `buzz_volume = count(comments) + w*count(videos)`
    - `sentiment = avg(comment_sentiment)`
    - `topics = top_k(keywords)`
- (고도화) `fact_youtube_trend_day_h3(day × h3_index)` — 매핑 성공 건만, coverage 표기

### Y5) 저장 모델(추가 테이블)

- raw: `raw_youtube_video`, `raw_youtube_comment`
- mart: `fact_youtube_trend_day_scope`, (옵션) `fact_youtube_trend_day_h3`
- vector(옵션): `youtube_comment_embedding(comment_id, embedding vector, metadata jsonb)`
    - 목적: “대표 코멘트 근거”를 RAG로 안전하게 인용

### Y6) 오케스트레이션(옵션 모듈)

- Supervisor에 **Social Agent** 추가:
    - “반응/댓글/트렌드/바이럴/키워드/감성/불만/칭찬” → Social Agent
    - “왜” 질문도 Social Agent 결과가 있으면 **정량+정성** 병렬 구성
- 모듈 OFF 시:
    - Social Agent 비활성, Insight Agent는 공공데이터 근거 + 한계/체크리스트 제공

## 5) 데이터 설계 (공공데이터 중심, 구현 가능한 수준)

### 5.1 (A) 데이터 소스 맵

- **필수 1순위**: D1(매출), D5(유동), D2(점포/개폐업), D3(상권영역), D9(행정동 경계), D11(실시간 보정)
- **보조 2순위**: D4(상주인구), D8(집객시설), D10(임대 대체), D14(실거래가), D15(임대·공실·수익률 통계)

### 5.2 (B) 표준 스키마 제안

- **dim_area**: (행정동/상권영역) `area_id`, `area_type`, `area_code`, `area_name`, `geom`
- **dim_category**: `cat_id`, `service_code`, `service_name`, (옵션) 상위/중위 코드
- **fact_sales_area_qtr**: `area_id`, `qtr`, `cat_id`, `sales_amt`, `sales_cnt`, (옵션) breakdown json
- **fact_flow_area_qtr**: `area_id`, `qtr`, (옵션) `flow_by_hour`, `flow_by_weekday`, `flow_by_demo`
- **fact_store_area_qtr**: `area_id`, `qtr`, `cat_id`, `store_cnt`, `open_cnt`, `close_cnt`
- **fact_realtime_congestion_area**(옵션): `area_id`, `ts`, `congestion_level`, `ppltn_min/max`
- **bridge_area_h3_weight**: `area_id`, `h3_index`, `weight` (폴리곤→H3 커버 결과)
- (P4용) **dim_asset**(옵션): `asset_id`, `address`, `lat/lng`, `owner_portfolio_tag`
- (P4용) **fact_deal_price_month**(옵션): `law_code5`, `yyyymm`, `price_per_sqm_p50/p75`, `n_deals`

### 5.3 (C) 정규화/표준화 규칙

- 단위 통일: `원`, `명`, `건`, `%(0~100)` / 날짜는 `YYYY-Q#` 또는 `timestamptz`
- 결측치: `null 유지 + coverage/confidence_score` 제공(분기별 표본 부족 시 경고)
- 이상치: QoQ 변화율 winsorize(예: 1~99%) 옵션 + 원본 값도 보관
- 코드 매핑: `서비스_업종_코드`는 `dim_category`에 정규화(명칭 변경 대비)
- 공간: 저장은 SRID 4326, 외부 EPSG:5181은 적재 시 변환
- “성수동 범위”: `preset_area_scope` 테이블로 관리(행정동/상권코드 집합)

### 5.4 (D) Hex(H3) 매핑 방법(단계)

1. `dim_area`에 상권/행정동 폴리곤 적재
2. H3 해상도 선택(res=9~10 권장; UI/성능 트레이드오프)
3. polyfill로 폴리곤을 H3로 커버
4. 폴리곤∩H3 교차면적 비율로 `weight` 산출
5. `bridge_area_h3_weight` 저장
6. 분기 fact를 H3로 변환: `sum(value * weight)`
7. 지도 렌더링은 `fact_*_h3_qtr`를 기본 테이블로 사용

### 5.5 (E) Supabase(Postgres+pgvector) 기준 DDL “의사코드”

```sql
create table dim_area (
  area_id bigserial primary key,
  area_type text check (area_type in ('ADMIN_DONG','COMMERCIAL_AREA')),
  area_code text not null,
  area_name text not null,
  geom geometry(MultiPolygon, 4326),
  unique(area_type, area_code)
);

create table dim_category (
  cat_id bigserial primary key,
  service_code text not null,
  service_name text not null,
  unique(service_code)
);

create table bridge_area_h3_weight (
  area_id bigint references dim_area(area_id),
  h3_index text not null,
  weight numeric not null check (weight >= 0),
  primary key(area_id, h3_index)
);

create table fact_sales_area_qtr (
  area_id bigint references dim_area(area_id),
  qtr text not null,
  cat_id bigint references dim_category(cat_id),
  sales_amt bigint,
  sales_cnt bigint,
  breakdown jsonb,
  confidence_score numeric default 1.0,
  primary key(area_id, qtr, cat_id)
);

create table fact_store_area_qtr (
  area_id bigint references dim_area(area_id),
  qtr text not null,
  cat_id bigint references dim_category(cat_id),
  store_cnt int,
  open_cnt int,
  close_cnt int,
  confidence_score numeric default 1.0,
  primary key(area_id, qtr, cat_id)
);

create table fact_flow_area_qtr (
  area_id bigint references dim_area(area_id),
  qtr text not null,
  flow_total bigint,
  flow_by_hour jsonb,
  flow_by_weekday jsonb,
  flow_by_demo jsonb,
  confidence_score numeric default 1.0,
  primary key(area_id, qtr)
);

create table fact_realtime_congestion_area (
  area_id bigint references dim_area(area_id),
  ts timestamptz not null,
  congestion_level text,
  ppltn_min int,
  ppltn_max int,
  primary key(area_id, ts)
);

create table analysis_run (
  run_id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  user_id text,
  persona_code text,
  question text,
  params_json jsonb,
  sql_text text,
  result_json jsonb,
  assumptions_json jsonb,
  data_asof jsonb
);

-- (옵션) P4 포트폴리오
create table dim_asset (
  asset_id uuid primary key default gen_random_uuid(),
  user_id text,
  label text,
  address text,
  lat numeric,
  lng numeric,
  cat_id bigint references dim_category(cat_id),
  created_at timestamptz default now()
);

create index on analysis_run(created_at);
create index on dim_area(area_type, area_code);
```

---

## 6) LLM 오케스트레이션(공공데이터 Q&A 중심) 설계

### 6.1 Supervisor 라우팅 규칙(요약)

- **SQL Agent로 라우팅**: “어디/언제/얼마/증가/감소/TopN/비교/A vs B/분기/시간대/요일/연령”
- **Insight Agent로 라우팅**: “왜/추천/리스크/전략/주의/다음 액션/요약/보고서”
- “최신/요즘/오늘” 포함: SQL 결과 + **D11(실시간) 보정 카드** 자동 동봉(가능한 범위에서)

### 6.2 SQL Agent 프롬프트(초안)

```
역할: 공공데이터 기반 상권 DB(Postgres)에서 안전하게 SQL을 생성한다.
목표: 자연어 질문을 허용된 테이블/컬럼만 사용해 1~3개의 SELECT SQL로 변환.

[안전규칙]
- SELECT만 허용. DDL/DML/서브쿼리 폭주 금지.
- 허용 테이블: dim_area, dim_category,
  fact_sales_area_qtr, fact_flow_area_qtr, fact_store_area_qtr,
  fact_realtime_congestion_area(옵션),
  bridge_area_h3_weight(공간 집계용)
- 기본 시간 범위: 최근 4개 분기.
- 결과 제한: 기본 LIMIT 200. TopN은 N<=20.
- 업종은 dim_category(service_code) → cat_id로 매핑.
- “성수동”은 preset_area_scope(사전 정의 area_id 집합)로 필터.

[출력]
- sql: (코드블록)
- rationale: 조인키/집계 요약
- data_asof: 사용 qtr / 실시간 포함 여부
```

### 6.3 Insight Agent 프롬프트(초안)

```
역할: SQL 결과를 해석해 "근거+주의사항+대안"으로 의사결정을 돕는다.
원칙:
- 근거 지표 3개 이상(숫자/증감률/순위) 인용
- 분기(후행) vs 실시간(nowcast) 구분
- 단정 금지: 추정/가능성/추가 확인 제시
- 추천 2개, 리스크 2개, 다음 액션 2개 필수

출력 포맷:
- 근거 데이터 카드(3개): metric, value, asof
- 핵심지표 3개
- 리스크 2개
- 추천 액션 2개
- 가정/제약
```

---

## 7) 검증/평가 계획

### 7.1 시나리오별 정답/근거 만들기(골든 쿼리/스냅샷/회귀)

- 시나리오별 **골든 SQL 3종** 저장(TopN / QoQ / A-B)
- 데이터 적재 시점마다 결과를 `analysis_run` 스냅샷으로 고정(회귀 기준)
- 회귀 테스트 체크:
    - 허용 테이블 준수(보안)
    - TopN 결과의 재현성(입력 동일 시 동일)
    - 증감 부호(+) / (-) 일관성
    - 응답시간/타임아웃/에러율

### 7.2 KPI를 유저 행동 이벤트로 측정(로그 스키마 초안)

- 이벤트 예시: `DASHBOARD_OPEN`, `HEX_CLICK`, `FILTER_APPLY`, `ASK`, `SAVE_RUN`, `EXPORT_PDF`, `SHARE_LINK`
- KPI 예시:
    - Engagement: 세션당 `ASK ≥ 3` 비율
    - Activation: `SAVE_RUN` 또는 `EXPORT_PDF` 전환율
    - Quality: SQL 성공률, 평균 응답시간, 에러율

---

## 8) 리스크/가정/미해결 질문

### 리스크

- R1 **분기 후행성**으로 “요즘” 질문 과대해석 → as-of 배지 + D11 보정 카드 + 변동성 경고
- R2 **상권코드↔︎행정동** 매핑이 근사/오차 → 공간조인 기준/버전 관리 + “근사치” 표기
- R3 **임대료/공실의 미시 데이터 부족** → 사용자 입력(가정) + 거시 통계(D15) 배지 + 대체지표(D10) 병행
- R4 (옵션) **유튜브 데이터 편향/노이즈**(노출 알고리즘/표본편향) → coverage/대표성 배지 + 정량과 분리 표기 + 단정 금지

### 가정(Assumption)

- A1 성수동 범위는 프리셋(area_scope)으로 관리하며, 상권/행정동은 공간조인으로 연결
- A2 최근 4개 분기는 “가용 최신 분기부터 역산”
- A3 운영/투자 파라미터(객단가/회전율/임대료/대출비율)는 사용자 입력(가정)으로 받는다

### 결정사항 반영(Resolved) / 추가조사(Backlog)

- **Q1 성수동 범위(상권코드 vs 행정동)** → **둘 다 지원(확정)**
    - `dim_area.area_type ∈ {admin_dong, commercial_area}`로 이원화
    - 분석 기본값은 **(행정동 프리셋 ∪ 상권 프리셋)**
    - 교차 분석이 필요할 때는 `area_mapping_admin_to_commercial`(공간조인 기반) 사용
- **Q2 H3 해상도(res)** → **기본 res=9(확정)**
    - UX 기본 줌(골목 단위)에서 “기둥 개수/프레임 레이트/해석성” 균형점으로 가정
    - 성능 이슈 발생 시: res=8(성능) / res=10(정밀)로 실험 플래그 제공
- **Q3 투자/임대 미시 데이터(공실/임대료)** → **임대료: ‘가능하면 우선 채택’, 공실: 대체지표 병행**
    - (확인) 서울시 **‘우리마을가게 상권분석서비스’**는 서비스 레벨에서 **‘임대시세’ 제공(범위 확대)**을 공지/언급합니다.
        - 근거(서울시 공지/기사):
            - https://news.seoul.go.kr/gov/archives/84465
            - https://mediahub.seoul.go.kr/archives/1147734
    - (현 상태) 다만 열린데이터광장/공공데이터포털에서 **“행정동/상권 단위 임대시세 파일/API”를 즉시 확인하지 못함** → **데이터 접근 경로 추가 확인 필요(Backlog)**
    - **채택 전략(우선순위)**
        1. **P0(가능 시 우선 채택)**: “임대시세(행정동/상권)” 공개 데이터가 확인되면 `fact_rent_price(area_type=admin_dong|commercial_area)`로 적재
        2. **P1(대체·거시)**: 한국부동산원 **상업용부동산 임대동향조사(분기·지역별)**로 **임대료/공실률/지수** 배지 제공
            - 공실률(소규모상가): https://www.data.go.kr/data/15069726/fileData.do
            - 임대료(집합상가): https://www.data.go.kr/data/15069791/fileData.do
            - 임대가격지수(소규모상가): https://www.data.go.kr/data/15069702/fileData.do
        3. **P2(Proxy·미시)**: 공실 “직접값” 대신 `점포수 증감/폐업신고율/개업-폐업 비율`로 “공실 리스크(간접)” 산출(시나리오 문서 참조)

---

## 부록) 데이터셋 단축 레퍼런스

- D1 추정매출(상권): https://data.seoul.go.kr/dataList/OA-15572/F/1/datasetView.do
- D2 점포(행정동): https://data.seoul.go.kr/dataList/OA-22172/S/1/datasetView.do
- D3 상권영역(공간): https://data.seoul.go.kr/dataList/OA-15560/S/1/datasetView.do
- D4 상주인구(행정동): https://data.seoul.go.kr/dataList/OA-22183/S/1/datasetView.do
- D5 생활/유동인구(상권): https://www.data.go.kr/data/15094719/fileData.do?recommendDataYn=Y
- D8 집객시설(상권배후지): https://data.seoul.go.kr/dataList/OA-15581/S/1/datasetView.do
- D9 행정동 경계(SHP): https://www.data.go.kr/data/15125055/fileData.do?recommendDataYn=Y
- D10 지하상가임대정보: https://data.seoul.go.kr/dataList/OA-12927/F/1/datasetView.do
- D11 실시간 도시데이터: https://data.seoul.go.kr/dataList/OA-21285/A/1/datasetView.do
- D14 상업업무용 실거래가(OpenAPI): https://www.data.go.kr/data/15126463/openapi.do
- D15 매장용빌딩 임대료·공실률·수익률 통계: https://data.seoul.go.kr/dataList/OA-12553/S/1/datasetView.do
- D16 한국부동산원 상업용부동산 임대동향조사 공실률(소규모상가): https://www.data.go.kr/data/15069726/fileData.do
- D17 한국부동산원 상업용부동산 임대동향조사 임대료(집합상가): https://www.data.go.kr/data/15069791/fileData.do
- D18 한국부동산원 상업용부동산 임대동향조사 임대가격지수(소규모상가): https://www.data.go.kr/data/15069702/fileData.do