-- Migration: 004_phase2_extensions.sql
-- Purpose: Phase 2-3 확장 (시간대 분석, 리스크 진단, 팝업, 기간비교)
-- Created: 2026-02-07

-- ============================================================================
-- 1. fact_facilities_area: D8 집객시설 데이터 (Phase 3)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fact_facilities_area (
    area_id         bigint NOT NULL REFERENCES dim_area(area_id),
    qtr             text NOT NULL,
    facility_type   text NOT NULL,           -- 집객시설 유형 (학교, 문화시설, 대형마트, 교통 등)
    facility_cnt    int NOT NULL DEFAULT 0,
    PRIMARY KEY (area_id, qtr, facility_type)
);

CREATE INDEX IF NOT EXISTS idx_facilities_area_qtr ON fact_facilities_area(area_id, qtr);

COMMENT ON TABLE fact_facilities_area IS 'D8 집객시설(상권배후지) 데이터';
COMMENT ON COLUMN fact_facilities_area.facility_type IS '시설 유형: 학교, 병원, 문화시설, 대형마트, 교통, 관공서 등';

-- ============================================================================
-- 2. content_brief: 콘텐츠 생성 결과 저장 (Phase 4)
-- ============================================================================
CREATE TABLE IF NOT EXISTS content_brief (
    brief_id        bigserial PRIMARY KEY,
    analysis_run_id bigint REFERENCES analysis_run(run_id),
    brief_type      text NOT NULL DEFAULT '4cut',   -- '4cut', 'script', 'report'
    goal            text,                            -- 입지추천, 리스크경고, 운영최적화
    content_json    jsonb NOT NULL,                  -- 4컷 구조 데이터
    citations       jsonb,                           -- KPI 근거 참조
    data_asof       text,
    created_at      timestamptz DEFAULT now()
);

COMMENT ON TABLE content_brief IS '콘텐츠 생성(4컷/스크립트) 결과 저장';
