-- 001_init_schema.sql
-- K-CIA Lite: 초기 스키마 생성
-- 실행: psql -f 001_init_schema.sql

BEGIN;

-- ============================================================
-- Extensions
-- ============================================================
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 차원 테이블
-- ============================================================

CREATE TABLE dim_area (
    area_id    bigserial PRIMARY KEY,
    area_type  text NOT NULL CHECK (area_type IN ('ADMIN_DONG', 'COMMERCIAL_AREA')),
    area_code  text NOT NULL,
    area_name  text NOT NULL,
    geom       geometry(MultiPolygon, 4326),
    UNIQUE (area_type, area_code)
);

CREATE TABLE dim_category (
    cat_id        bigserial PRIMARY KEY,
    service_code  text NOT NULL UNIQUE,
    service_name  text NOT NULL
);

CREATE TABLE preset_area_scope (
    scope_id   bigserial PRIMARY KEY,
    area_id    bigint NOT NULL REFERENCES dim_area(area_id),
    area_type  text NOT NULL CHECK (area_type IN ('ADMIN_DONG', 'COMMERCIAL_AREA'))
);

-- ============================================================
-- 브릿지 테이블
-- ============================================================

CREATE TABLE bridge_area_h3_weight (
    area_id   bigint NOT NULL REFERENCES dim_area(area_id),
    h3_index  text   NOT NULL,
    weight    numeric NOT NULL CHECK (weight >= 0),
    PRIMARY KEY (area_id, h3_index)
);

CREATE INDEX idx_bridge_h3_index ON bridge_area_h3_weight(h3_index);

-- ============================================================
-- 팩트 테이블
-- ============================================================

CREATE TABLE fact_sales_area_qtr (
    area_id           bigint  NOT NULL REFERENCES dim_area(area_id),
    qtr               text    NOT NULL,
    cat_id            bigint  NOT NULL REFERENCES dim_category(cat_id),
    sales_amt         bigint,
    sales_cnt         bigint,
    breakdown         jsonb,
    confidence_score  numeric DEFAULT 1.0,
    PRIMARY KEY (area_id, qtr, cat_id)
);

CREATE TABLE fact_flow_area_qtr (
    area_id           bigint  NOT NULL REFERENCES dim_area(area_id),
    qtr               text    NOT NULL,
    flow_total        bigint,
    flow_by_hour      jsonb,
    flow_by_weekday   jsonb,
    flow_by_demo      jsonb,
    confidence_score  numeric DEFAULT 1.0,
    PRIMARY KEY (area_id, qtr)
);

CREATE TABLE fact_store_area_qtr (
    area_id           bigint  NOT NULL REFERENCES dim_area(area_id),
    qtr               text    NOT NULL,
    cat_id            bigint  NOT NULL REFERENCES dim_category(cat_id),
    store_cnt         int,
    open_cnt          int,
    close_cnt         int,
    franchise_cnt     int,
    confidence_score  numeric DEFAULT 1.0,
    PRIMARY KEY (area_id, qtr, cat_id)
);

CREATE TABLE fact_realtime_congestion_area (
    area_id           bigint      NOT NULL REFERENCES dim_area(area_id),
    ts                timestamptz NOT NULL,
    congestion_level  text,
    ppltn_min         int,
    ppltn_max         int,
    PRIMARY KEY (area_id, ts)
);

-- ============================================================
-- 분석 로그
-- ============================================================

CREATE TABLE analysis_run (
    run_id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at       timestamptz DEFAULT now(),
    user_id          text,
    persona_code     text,
    question         text,
    params_json      jsonb,
    sql_text         text,
    result_json      jsonb,
    assumptions_json jsonb,
    data_asof        jsonb
);

CREATE INDEX idx_analysis_run_created ON analysis_run(created_at);

-- ============================================================
-- 이벤트 로그
-- ============================================================

CREATE TABLE event_log (
    event_id   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz DEFAULT now(),
    event_type text        NOT NULL,
    session_id text,
    user_id    text,
    props      jsonb
);

CREATE INDEX idx_event_log_created ON event_log(created_at);
CREATE INDEX idx_event_log_type ON event_log(event_type);
CREATE INDEX idx_event_log_props ON event_log USING GIN (props);

-- ============================================================
-- 수집 메타
-- ============================================================

CREATE TABLE ingest_runs (
    run_id            bigserial   PRIMARY KEY,
    dataset_id        text        NOT NULL,
    started_at        timestamptz DEFAULT now(),
    finished_at       timestamptz,
    status            text        NOT NULL CHECK (status IN ('success', 'failure', 'partial')),
    source_updated_at timestamptz,
    fetched_objects   int,
    row_count         int,
    checksum          text,
    error_message     text
);

CREATE TABLE raw_objects (
    object_id       uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id      text        NOT NULL,
    storage_path    text        NOT NULL,
    content_type    text,
    bytes           bigint,
    md5             text,
    fetched_at      timestamptz DEFAULT now(),
    logical_period  text
);

CREATE TABLE schema_registry (
    dataset_id           text        NOT NULL,
    header_hash          text        NOT NULL,
    columns_json         jsonb,
    first_seen_at        timestamptz DEFAULT now(),
    last_seen_at         timestamptz DEFAULT now(),
    breaking_change_flag boolean     DEFAULT false,
    PRIMARY KEY (dataset_id, header_hash)
);

COMMIT;
