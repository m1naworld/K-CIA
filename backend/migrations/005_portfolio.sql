-- Migration: 005_portfolio.sql
-- Purpose: Phase 5 포트폴리오 관리 + D14/D15 데이터 테이블
-- Created: 2026-02-07

-- ============================================================================
-- 1. dim_asset: 사용자 점포 등록
-- ============================================================================
CREATE TABLE IF NOT EXISTS dim_asset (
    asset_id        bigserial PRIMARY KEY,
    user_id         text,                    -- 사용자 식별자 (세션 기반)
    address         text NOT NULL,
    lat             numeric,
    lng             numeric,
    h3_index        text,                    -- H3 인덱스 (res=10)
    area_id         bigint REFERENCES dim_area(area_id),
    category        text,                    -- 업종
    memo            text,
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_asset_user ON dim_asset(user_id);
CREATE INDEX IF NOT EXISTS idx_asset_h3 ON dim_asset(h3_index);

COMMENT ON TABLE dim_asset IS '사용자 등록 점포(자산) 정보';

-- ============================================================================
-- 2. fact_real_price: D14 상업업무용 실거래가
-- ============================================================================
CREATE TABLE IF NOT EXISTS fact_real_price (
    price_id        bigserial PRIMARY KEY,
    area_id         bigint REFERENCES dim_area(area_id),
    contract_ym     text NOT NULL,           -- 계약년월 (YYYYMM)
    price_per_sqm   numeric,                 -- 단가 (원/㎡)
    total_price     numeric,                 -- 거래금액
    floor_no        int,                     -- 층
    area_sqm        numeric,                 -- 전용면적
    building_age    int,                     -- 건축년도로 계산한 건물나이
    dong_code       text                     -- 법정동코드
);

CREATE INDEX IF NOT EXISTS idx_real_price_area ON fact_real_price(area_id, contract_ym);

COMMENT ON TABLE fact_real_price IS 'D14 상업업무용 실거래가 데이터';

-- ============================================================================
-- 3. fact_rent_vacancy: D15 임대료/공실률/수익률
-- ============================================================================
CREATE TABLE IF NOT EXISTS fact_rent_vacancy (
    rv_id           bigserial PRIMARY KEY,
    area_id         bigint REFERENCES dim_area(area_id),
    qtr             text NOT NULL,
    rent_per_sqm    numeric,                 -- 임대료 (원/㎡/월)
    vacancy_rate    numeric,                 -- 공실률 (0.0~1.0)
    yield_rate      numeric,                 -- 수익률 (0.0~1.0)
    building_type   text                     -- 건물유형 (소규모상가, 집합상가 등)
);

CREATE INDEX IF NOT EXISTS idx_rent_vacancy_area ON fact_rent_vacancy(area_id, qtr);

COMMENT ON TABLE fact_rent_vacancy IS 'D15 매장용빌딩 임대료/공실률/수익률 통계';

-- ============================================================================
-- 4. portfolio_snapshot: 포트폴리오 스냅샷
-- ============================================================================
CREATE TABLE IF NOT EXISTS portfolio_snapshot (
    snapshot_id     bigserial PRIMARY KEY,
    user_id         text,
    assets_json     jsonb NOT NULL,          -- 점포 목록 + 지표
    metrics_json    jsonb,                   -- 전체 메트릭
    recommendations_json jsonb,              -- 리밸런싱 권고
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_portfolio_user ON portfolio_snapshot(user_id);

COMMENT ON TABLE portfolio_snapshot IS '포트폴리오 분석 스냅샷';
