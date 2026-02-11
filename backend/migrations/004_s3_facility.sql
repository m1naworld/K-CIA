-- Migration: 004_s3_facility.sql
-- Purpose: D8 집객시설(상권배후지) 분기별 시설 유형별 건수 저장
-- Source: Seoul API VwsmTrdarHitterIndQq (OA-15581)
-- Created: 2026-02-07

BEGIN;

-- ============================================================================
-- fact_facility_area_qtr: 상권배후지별 집객시설 (narrow/EAV format)
-- ============================================================================
-- facility_type 예시: SUBWAY_STATN, BUS_STTN, BANK, GNRL_HSPTL, UNIV 등
-- M6-2 ETL에서 실제 API 컬럼 확인 후 매핑

CREATE TABLE IF NOT EXISTS fact_facility_area_qtr (
    area_id        bigint NOT NULL REFERENCES dim_area(area_id),
    qtr            text   NOT NULL,
    facility_type  text   NOT NULL,
    facility_cnt   int    NOT NULL DEFAULT 0,
    PRIMARY KEY (area_id, qtr, facility_type)
);

CREATE INDEX IF NOT EXISTS idx_fact_facility_area_qtr
    ON fact_facility_area_qtr(area_id, qtr);

COMMENT ON TABLE fact_facility_area_qtr
    IS 'D8 집객시설(상권배후지) - 분기별 시설 유형별 건수';
COMMENT ON COLUMN fact_facility_area_qtr.facility_type
    IS '시설 유형 코드 (SUBWAY_STATN, BANK, GNRL_HSPTL 등)';

COMMIT;
