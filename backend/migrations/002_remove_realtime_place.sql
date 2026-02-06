-- 002_remove_realtime_place.sql
-- REALTIME_PLACE 행 제거 및 area_type CHECK 제약조건 정리
-- D11 실시간 데이터는 기존 COMMERCIAL_AREA에 매핑

BEGIN;

-- 기존 REALTIME_PLACE의 fact 데이터 삭제
DELETE FROM fact_realtime_congestion_area
WHERE area_id IN (
    SELECT area_id FROM dim_area WHERE area_type = 'REALTIME_PLACE'
);

-- REALTIME_PLACE 행 삭제
DELETE FROM dim_area WHERE area_type = 'REALTIME_PLACE';

-- CHECK 제약조건 재설정 (REALTIME_PLACE 제거)
ALTER TABLE dim_area DROP CONSTRAINT IF EXISTS dim_area_area_type_check;
ALTER TABLE dim_area ADD CONSTRAINT dim_area_area_type_check
    CHECK (area_type IN ('ADMIN_DONG', 'COMMERCIAL_AREA'));

COMMIT;
