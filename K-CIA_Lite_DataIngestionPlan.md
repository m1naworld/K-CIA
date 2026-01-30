# K-CIA Lite — 데이터 수집(ingestion) 상세 계획서  
작성일: 2026-01-30  
대상: **성수동(행정동 기준 + 상권코드 기준 “둘 다” 지원)**, 최근 4개 분기(기본) + 실시간(nowcast) 신호

---

## 0) 수집 설계 원칙 (실행 우선)
- **공공데이터 1순위**: 분기(후행) 데이터는 “사실(fact)”로, **실시간 데이터는 “보정/nowcast 신호”**로 분리
- **Idempotent(멱등) 수집**: 같은 분기/같은 파일을 다시 받아도 결과 동일(Upsert 키 고정)
- **원본 보관**: 모든 원본(zip/csv/json)을 Supabase Storage(or S3)에 저장 → 재현/감사/회귀테스트 가능
- **후행성 UX 노출**: 각 지표 카드에 `as_of_quarter`, `source_updated_at`, `lag_label(예: “약 3개월 후행”)`을 **항상** 표기
- **영역 이원화(Q1 반영)**:  
  - `행정동(ADSTRD)` 지표 + `상권영역(상권_코드)` 지표를 **동시에 적재**  
  - UI 토글: “행정동/상권”  
  - 데이터 모델: `dim_area(area_type)` + `bridge_area_map(행정동↔상권)`로 양방향 조회

---

## 1) 전체 수집 아키텍처 (권장)
### 1.1 컴포넌트
1) **Scheduler/Orchestrator**: Prefect(추천) 또는 Airflow / 혹은 초기에는 Cron + Python  
2) **Collectors (데이터 소스별 커넥터)**  
   - `seoul_open_data_zip_collector` (ZIP 다운로드형)  
   - `seoul_open_api_collector` (OpenAPI 호출형)  
   - `data_go_kr_file_collector` (fileData 다운로드형)  
   - `boundary_file_collector` (SHP/GeoJSON/CSV 경계 파일)  
   - `youtube_collector` (옵션 모듈, 일 단위)
3) **Raw Storage**: Supabase Storage(bucket: `raw/`)  
4) **Staging DB(Postgres)**: `stg_*` (원본 스키마 최대 유지)  
5) **Warehouse(모델링)**: `dim_*`, `fact_*`, `bridge_*`  
6) **Derived/Serving**: `agg_*`(Hex res=9 기본), `mv_*`(materialized view)  

### 1.2 수집 파이프라인(표준 흐름)
**(A) Discover** 최신 버전 탐지(수정일, 파일명, 기준 분기)  
→ **(B) Fetch** 다운로드/API 호출  
→ **(C) Persist raw** 원본을 스토리지에 저장 + 메타데이터 기록  
→ **(D) Parse** unzip/CSV parse/JSON normalize  
→ **(E) Load stg** COPY 로딩(대량) + 스키마 드리프트 감지  
→ **(F) Upsert fact/dim** 키 기반 Upsert + 파티셔닝(분기)  
→ **(G) Build aggregates** 최근 4개 분기 + QoQ, TopN, Hex res=9  
→ **(H) Quality & Alert** rowcount/NULL/범위 체크 + 알림

---

## 2) 데이터 소스별 수집 상세 계획 (필수 1순위 + 보조 2순위)
> “실제 구현” 관점에서 **수집 방식 / 주기 / 후행성 / 증분 로직 / 저장 키**를 확정합니다.

### 2.1 필수 1순위 — 매출/유동/점포/영역
#### D1. 추정매출(상권) — 서울시 상권분석서비스(추정매출-상권)
- 출처/링크: 서울 열린데이터광장 OA-15572 citeturn0search2  
- 형태: **ZIP 다운로드(연도별)** (sheet API가 있더라도 1,000건 제한 가능 → 원칙적으로 ZIP)  
- 수집 주기: **분기 1회**(월 1회로 최신 여부 체크)  
- 후행성: 통상 **약 1~3개월 후행**(카드사/보정 로직 반영) — UI 라벨로 고정 표기  
- 증분 로직:
  - 최근 4개 분기만 “강제 재적재(재계산 대비)”  
  - 키: `(기준_년분기_코드, 상권_코드, 서비스_업종_코드)`  
- Raw 저장:
  - `raw/seoul/OA-15572/{year}/OA-15572_{year}_{downloaded_at}.zip`
- Staging:
  - `stg_sales_commercial`(CSV 헤더 그대로)  
- Warehouse Upsert:
  - `fact_sales(area_type='commercial', area_id=상권_코드, quarter=기준_년분기_코드, category=서비스_업종_코드, metrics...)`

#### D2. 점포(행정동) — 서울시 상권분석서비스(점포-행정동)
- 출처/링크: 서울 열린데이터광장 OA-22172 citeturn0search1  
- 형태: **ZIP 다운로드(연도별)**  
- 수집 주기: **분기 1회**(월 1회 최신 체크)  
- 후행성: 분기 데이터(대체로 1~3개월 후행)  
- 증분 로직:
  - 최근 4개 분기 재적재  
  - 키: `(기준_년분기_코드, 행정동_코드, 서비스_업종_코드)`  
- Raw 저장:
  - `raw/seoul/OA-22172/{year}/OA-22172_{year}_{downloaded_at}.zip`
- Warehouse Upsert:
  - `fact_store_count(area_type='admin_dong', area_id=행정동_코드, quarter, category, store_cnt, open_cnt, close_cnt, franchise_cnt...)`

#### D3. 상권영역(상권코드 ↔ 공간) — 상권분석서비스(영역-상권)
- 출처/링크: 공공데이터포털 fileData(영역-상권) citeturn8search4  
- 형태: **CSV(좌표/면적/코드)** (가능하면 폴리곤 제공 여부 확인; 없으면 중심점+면적으로 최소 구현)  
- 수집 주기: **연 1회**(또는 변경 시)  
- 역할: “상권코드 ↔ 지도 표시/공간조인 기반”의 기준 테이블  
- Raw 저장:
  - `raw/datagokr/15076394/area_commercial_{downloaded_at}.csv`
- Warehouse:
  - `dim_area(area_type='commercial', area_id=상권_코드, name, centroid, area_m2, geom?)`
  - 폴리곤이 없을 경우: MVP는 centroid 기반 Hex 근사(추후 폴리곤 확보 시 업그레이드)

#### D5. 생활/유동인구(상권) — 상권-생활인구(시간대/요일/성별/연령)
- 출처/링크: 공공데이터포털 fileData 15094719 citeturn8search5  
- 형태: **CSV 다운로드**  
- 수집 주기: **분기 1회**(월 1회 최신 체크)  
- 후행성: 분기 후행(통상 1~3개월)  
- 증분 로직:
  - 최근 4개 분기 재적재  
  - 키: `(기준_년분기_코드, 상권_코드)` + 세부 차원(시간대/요일/성별/연령대 등)  
- Warehouse:
  - `fact_flow(area_type='commercial', area_id=상권_코드, quarter, time_bucket, dow, sex, age_band, flow_cnt...)`
  - 서빙용: `agg_flow_peak`(피크 시간대/주말비중 등)

---

### 2.2 보조 2순위 — 후행성 보정/설명력/리스크(임대 포함)
#### D11. 실시간 도시데이터(주요 120장소) — “즉시성(nowcast)” 신호
- 출처/링크: 서울 열린데이터광장 OA-21285 (실시간 도시데이터) citeturn2search3  
- 형태: **OpenAPI(JSON)** — 분/시간 단위 혼잡도·현황성 지표  
- 수집 주기: **5분~15분 주기**(초기 15분 추천)  
- 저장 전략(중요):
  - 공공 분기 데이터의 후행성 보정을 위해 **스냅샷을 우리 DB에 시계열로 적재**  
  - 키: `(place_id(area_cd), ts)`  
  - 보관 정책: 90일(원시), 365일(집계)  
- Warehouse:
  - `fact_nowcast(place_id, ts, congestion_level, ppltn, weather?, events?, ...)`
  - `bridge_place_to_area`(place ↔ 행정동/상권 매핑; 초기엔 수동 매핑 테이블로 시작)

#### D-Rent. 임대시세(행정동/자치구) — 투자/임대 페르소나 핵심
- “가능하면 우선 채택(Q3)” 판단 근거:
  - 서울시 상권분석서비스(골목상권) 데이터 출처 문서에서 **임대시세(환산임대료)**가 **행정동/자치구 단위**, **분기 주기**로 제공됨 citeturn10view0turn12search5  
  - 환산임대료 정의/산식(보증금, 월세 기반 추정) 및 “현장 확인 필요” 안내가 명시됨 citeturn12search5  
- 수집 방법(우선순위):
  1) **공식 공개 데이터셋(최우선)**: 서울 열린데이터광장/공공데이터포털에 “임대시세(행정동)” 파일/오픈API가 존재하는지 확정(탐색/문의).  
  2) (대안) **정책/리포트 Export 경로**: golmok 서비스에서 제공하는 행정동 임대시세를 파일로 제공하는 공식 Export가 있다면 그 경로 활용(이용약관/로봇 정책 확인 필수).  
  3) (대체) **공개 지표로 근사**: 구 단위 상업용 임대지수(공식 기관) + 점포변화/공실 프록시(폐업률/점포감소)로 “임대 압력 지수” 구성  
- 주기/후행성:
  - 기본: **분기 1회**, 후행성 표기(“분기 후행”)  
- Warehouse(목표 스키마):
  - `fact_rent(area_type='admin_dong', area_id=행정동_코드, quarter, rent_equiv, deposit_median?, monthly_rent_median?, source_note)`
  - `risk_rent_pressure`(QoQ, 상위분위)

---

## 3) “성수동 범위” 수집 파라미터 확정 (행정동 + 상권)
### 3.1 행정동(기본 프리셋)
- 성수1가1동 / 성수1가2동 / 성수2가1동 / 성수2가3동  
- 수집 쿼리의 `area_id` 필터는 이 4개를 기본 포함(향후 사용자 확장 가능)

### 3.2 상권코드(골목상권)
- `dim_area(area_type='commercial')`에서 성수동 주변 상권을 **초기 20~40개 후보**로 지정  
- 후보 생성 방식:
  - (A) 상권영역(영역-상권)에서 성수동 행정동 폴리곤과 **교차(intersect) 면적 비율**이 높은 상권코드  
  - (B) 유저가 지도에서 클릭한 영역 기반으로 “즐겨찾기 상권” 추가

---

## 4) 수집 메타데이터/운영 테이블(필수)
### 4.1 ingest_runs (수집 실행 로그)
- 목적: 재현성/알림/회귀테스트/재시도 제어  
- 주요 컬럼:
  - `run_id, dataset_id, started_at, finished_at, status, source_updated_at, fetched_objects, row_count, checksum, error_message`

### 4.2 raw_objects (원본 파일/응답 저장 인덱스)
- `object_id, dataset_id, storage_path, content_type, bytes, md5, fetched_at, logical_period(예: 2025Q3)`

### 4.3 schema_registry (스키마 드리프트 감지)
- `dataset_id, header_hash, columns_json, first_seen_at, last_seen_at, breaking_change_flag`

---

## 5) YouTube(옵션 모듈) 수집 계획 — “없어도 성립” + “있으면 트렌드 보정”
> 소셜은 **옵션**이며, 공공데이터 Q&A가 기본 기능으로 성립해야 함(원칙 유지).

### 5.1 수집 대상 정의(성수동 트렌드)
- 쿼리 seed:
  - 키워드: “성수동 카페”, “성수 팝업”, “연무장길”, “뚝섬역 맛집”, “성수 디저트”  
- 수집 범위:
  - 최근 90일 업로드(기본), 조회수/댓글수 임계치로 필터  
- 수집 주기:
  - **일 1회**(새 영상/새 댓글 incremental)

### 5.2 데이터 모델(요약)
- `yt_video(video_id, published_at, channel_id, title, view_count, like_count, comment_count, query_seed, fetched_at)`
- `yt_comment(comment_id, video_id, published_at, author_hash, text, like_count, fetched_at)`
- `yt_insight(video_id, run_date, sentiment_score, topics_json, complaint_tags_json, summary)`

### 5.3 “유튜브가 없을 때” 답변 전략
- UI에서 “트렌드(옵션)” 토글 OFF 시:
  - 결과 카드에서 “정성 트렌드 데이터 없음 → 공공데이터 기반 결과만 제공” 문구 고정  
  - nowcast(D11)가 있으면 “실시간 혼잡도”를 트렌드 대체 신호로 활용

---

## 6) 구현 체크리스트(개발 우선순위)
### Sprint 1 (MVP, 1~2주)
- [ ] Supabase 프로젝트 + Storage bucket(`raw`) 생성  
- [ ] `ingest_runs/raw_objects/schema_registry` 테이블 생성  
- [ ] D1/D2/D5 “ZIP/CSV 다운로드형” 수집기 3종 구현  
- [ ] 최근 4개 분기 적재 + `fact_sales/fact_store_count/fact_flow` upsert  
- [ ] UI에 `as_of_quarter` / `lag_label` 노출

### Sprint 2 (지도/공간 + nowcast, 1~2주)
- [ ] D3(영역-상권) + `dim_area` 적재  
- [ ] 행정동(성수 4개) 경계 연결(폴리곤 확보)  
- [ ] H3 res=9 Hex 집계(최근 4개 분기)  
- [ ] D11 실시간 도시데이터 수집 + 스냅샷 저장

### Sprint 3 (임대/투자 + 유튜브 옵션, 1~2주)
- [ ] 임대시세 데이터 공개 경로 확정(공식 파일/오픈API 우선) citeturn10view0turn12search5  
- [ ] `fact_rent` 적재 + “임대 압력” 지표 생성  
- [ ] YouTube 수집 모듈(옵션) + 토픽/감성 요약(일 배치)

---

## 7) 수집 코드 의사코드(공통)
### 7.1 ZIP 다운로드형 (서울 열린데이터광장)
```python
def ingest_zip_dataset(dataset_id, year):
    meta = discover_latest(dataset_id, year)  # 수정일/파일명/다운로드 URL
    if already_ingested(meta.checksum): return

    zip_bytes = http_get(meta.download_url, timeout=60)
    path = storage_put(f"raw/seoul/{dataset_id}/{year}/{meta.filename}", zip_bytes)

    rows = []
    for csv in unzip(zip_bytes):
        df = read_csv(csv, encoding="utf-8-sig")
        validate_schema(df, dataset_id)
        load_to_stg(df, table=f"stg_{dataset_id.lower()}")

    upsert_fact_dim(dataset_id)   # PK 키 기반
    build_aggregates(dataset_id)  # 최근 4분기, QoQ, TopN
    record_run_success(...)
```

### 7.2 OpenAPI(JSON) 스냅샷형 (실시간 도시데이터)
```python
def ingest_nowcast(area_cd_list):
    for area_cd in area_cd_list:
        data = http_get_json(f"/api/{area_cd}")
        ts = now()
        storage_put_json(f"raw/seoul/OA-21285/{area_cd}/{ts}.json", data)
        upsert("fact_nowcast", normalize(data, ts=ts, place_id=area_cd))
```

---

## 8) 미해결/가정(Assumptions) — 수집 관점
- A1) 서울 열린데이터광장 ZIP 다운로드 URL을 자동으로 “발견(discover)”할 수 있다(HTML 구조 변경 시 대응 필요)  
- A2) 상권영역(영역-상권)에 폴리곤이 없을 수 있음 → MVP는 centroid 기반, 후속으로 폴리곤 확보/대체  
- A3) 임대시세(환산임대료)는 “행정동/자치구 단위 분기 데이터”가 존재하나, **공식 개방 파일/API 경로는 추가 확인 필요** citeturn10view0turn12search5  

---
