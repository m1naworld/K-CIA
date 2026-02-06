-- Migration: 003_store_h3_weight.sql
-- Purpose: 점포 수 기반 H3 Weight 계산을 위한 테이블
-- Created: 2026-02-04

-- ============================================================================
-- 1. raw_semas_store: 소상공인 상가정보 원본 저장
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_semas_store (
    store_id        text PRIMARY KEY,           -- bizesId (상가업소번호)
    store_name      text,                       -- bizesNm (상호명)
    branch_name     text,                       -- brchNm (지점명)
    inds_l_cd       text,                       -- 대분류 코드
    inds_l_nm       text,                       -- 대분류명
    inds_m_cd       text,                       -- 중분류 코드
    inds_m_nm       text,                       -- 중분류명
    inds_s_cd       text,                       -- 소분류 코드
    inds_s_nm       text,                       -- 소분류명
    addr_road       text,                       -- 도로명주소 (rdnmAdr)
    lng             numeric,                    -- 경도 (lon)
    lat             numeric,                    -- 위도 (lat)
    h3_index        text,                       -- H3 인덱스 (res=9)
    adong_cd        text,                       -- 행정동코드
    fetched_at      timestamptz DEFAULT now()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_raw_semas_h3 ON raw_semas_store(h3_index);
CREATE INDEX IF NOT EXISTS idx_raw_semas_adong ON raw_semas_store(adong_cd);
CREATE INDEX IF NOT EXISTS idx_raw_semas_inds_l ON raw_semas_store(inds_l_cd);
CREATE INDEX IF NOT EXISTS idx_raw_semas_inds_m ON raw_semas_store(inds_m_cd);

COMMENT ON TABLE raw_semas_store IS '소상공인시장진흥공단 상가정보 API 원본 데이터';
COMMENT ON COLUMN raw_semas_store.store_id IS '상가업소번호 (bizesId) - API 고유 ID';
COMMENT ON COLUMN raw_semas_store.h3_index IS 'H3 인덱스 (resolution 9)';

-- ============================================================================
-- 2. fact_store_h3_count: H3별 점포 수 집계
-- ============================================================================
CREATE TABLE IF NOT EXISTS fact_store_h3_count (
    h3_index        text PRIMARY KEY,
    store_cnt       int NOT NULL,
    updated_at      timestamptz DEFAULT now()
);

COMMENT ON TABLE fact_store_h3_count IS 'H3 헥사곤별 점포 수 집계';

-- ============================================================================
-- 3. bridge_area_h3_weight_store: 점포 수 기반 H3 weight
-- ============================================================================
CREATE TABLE IF NOT EXISTS bridge_area_h3_weight_store (
    area_id         bigint NOT NULL REFERENCES dim_area(area_id),
    h3_index        text NOT NULL,
    store_cnt       int NOT NULL,
    weight          numeric NOT NULL,
    calculated_at   timestamptz DEFAULT now(),
    PRIMARY KEY (area_id, h3_index)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_bridge_store_h3 ON bridge_area_h3_weight_store(h3_index);
CREATE INDEX IF NOT EXISTS idx_bridge_store_area ON bridge_area_h3_weight_store(area_id);

COMMENT ON TABLE bridge_area_h3_weight_store IS '점포 수 기반 상권-H3 가중치 매핑';
COMMENT ON COLUMN bridge_area_h3_weight_store.weight IS '해당 H3의 점포 수 / 상권 전체 점포 수';

-- ============================================================================
-- 4. 검증 쿼리 (실행용 아님, 참고용)
-- ============================================================================
-- 점포 수 검증:
-- SELECT adong_cd, count(*) FROM raw_semas_store GROUP BY adong_cd;
-- SELECT count(DISTINCT h3_index) FROM raw_semas_store;

-- Weight 합계 검증 (1.0이어야 함):
-- SELECT area_id, sum(weight) FROM bridge_area_h3_weight_store
-- GROUP BY area_id HAVING abs(sum(weight) - 1.0) > 0.01;
