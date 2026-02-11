-- Migration: 005_sns_module.sql
-- Purpose: SNS 모듈 테이블 (YouTube + Naver Blog/Cafe 트렌드)
-- References: DEC-016 (YouTube+Naver 확장), DEC-021 (best-effort 상권 매핑)
-- Created: 2026-02-09

BEGIN;

-- ============================================================================
-- fact_social_trend_daily: 소셜 트렌드 일별 집계
-- ============================================================================
-- source: 'youtube' | 'naver_blog' | 'naver_cafe'
-- area_id: nullable FK → 상권 수준 매핑 (best-effort, NULL=미매핑→성수동 전체)
-- evidence_snippets: JSONB 배열 [{title, url, published_at, snippet}]
-- top_keywords: JSONB 배열 ["키워드1", "키워드2", ...]

CREATE TABLE IF NOT EXISTS fact_social_trend_daily (
    trend_id           bigserial   PRIMARY KEY,
    area_id            bigint      REFERENCES dim_area(area_id),  -- NULL=성수동 전체
    source             text        NOT NULL CHECK (source IN ('youtube', 'naver_blog', 'naver_cafe')),
    collected_date     date        NOT NULL,
    keyword            text        NOT NULL,
    buzz_volume        int         NOT NULL DEFAULT 0,
    sentiment_score    numeric(4,3),
    sentiment_pos      int         DEFAULT 0,
    sentiment_neg      int         DEFAULT 0,
    top_keywords       jsonb,
    evidence_snippets  jsonb,
    created_at         timestamptz DEFAULT now()
);

-- NULL area_id도 중복 방지 (PostgreSQL 15+ NULLS NOT DISTINCT)
CREATE UNIQUE INDEX IF NOT EXISTS uq_social_trend_daily
    ON fact_social_trend_daily (area_id, source, collected_date, keyword)
    NULLS NOT DISTINCT;

CREATE INDEX IF NOT EXISTS idx_social_trend_date
    ON fact_social_trend_daily(collected_date);
CREATE INDEX IF NOT EXISTS idx_social_trend_source
    ON fact_social_trend_daily(source, collected_date);
CREATE INDEX IF NOT EXISTS idx_social_trend_keyword
    ON fact_social_trend_daily(keyword);
CREATE INDEX IF NOT EXISTS idx_social_trend_area
    ON fact_social_trend_daily(area_id)
    WHERE area_id IS NOT NULL;

COMMENT ON TABLE fact_social_trend_daily
    IS 'SNS 트렌드 일별 집계 (YouTube, Naver Blog/Cafe)';
COMMENT ON COLUMN fact_social_trend_daily.area_id
    IS '상권 FK (best-effort 매핑, NULL=성수동 전체 수준)';
COMMENT ON COLUMN fact_social_trend_daily.source
    IS '데이터 소스 (youtube, naver_blog, naver_cafe)';
COMMENT ON COLUMN fact_social_trend_daily.sentiment_score
    IS '감성 점수 (-1.0 ~ 1.0, NULL=미분석)';
COMMENT ON COLUMN fact_social_trend_daily.evidence_snippets
    IS 'JSONB 배열: [{title, url, published_at, snippet}]';

-- ============================================================================
-- social_module_config: SNS 모듈 설정 (ON/OFF 등)
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_module_config (
    config_key    text        PRIMARY KEY,
    config_value  text        NOT NULL,
    updated_at    timestamptz DEFAULT now()
);

-- 기본값: SNS 모듈 비활성화
INSERT INTO social_module_config (config_key, config_value)
VALUES
    ('enabled', 'false'),
    ('youtube_enabled', 'false'),
    ('naver_enabled', 'false'),
    ('default_keywords', '["성수동 카페","성수동 맛집","성수동 팝업","성수 브런치","성수 디저트"]'),
    ('collection_days', '30')
ON CONFLICT (config_key) DO NOTHING;

COMMENT ON TABLE social_module_config
    IS 'SNS 모듈 설정 (enabled=false가 기본, ON/OFF 토글)';

COMMIT;
