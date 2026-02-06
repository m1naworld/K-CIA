"""Data API: 업종 목록, 영역 프리셋."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import get_db

router = APIRouter(prefix="/api/data", tags=["data"])


# ── Response models ───────────────────────────────────────────


class CategoryItem(BaseModel):
    cat_id: int
    service_code: str
    service_name: str


class CategoriesResponse(BaseModel):
    data: list[CategoryItem]
    total: int


class AreaScopeItem(BaseModel):
    area_id: int
    area_type: str
    area_code: str
    area_name: str


class AreaScopeResponse(BaseModel):
    data: list[AreaScopeItem]
    total: int


# ── Endpoints ─────────────────────────────────────────────────


@router.get("/categories", response_model=CategoriesResponse)
def get_categories(db: Session = Depends(get_db)):
    """업종 목록 조회."""
    rows = db.execute(
        text("SELECT cat_id, service_code, service_name FROM dim_category ORDER BY service_code")
    ).fetchall()
    items = [CategoryItem(cat_id=r[0], service_code=r[1], service_name=r[2]) for r in rows]
    return CategoriesResponse(data=items, total=len(items))


@router.get("/area-scope", response_model=AreaScopeResponse)
def get_area_scope(
    area_type: str | None = None,
    db: Session = Depends(get_db),
):
    """영역 프리셋 조회 (행정동/상권 필터 가능)."""
    sql = """
        SELECT a.area_id, a.area_type, a.area_code, a.area_name
        FROM dim_area a
        INNER JOIN preset_area_scope p ON a.area_id = p.area_id
    """
    params: dict = {}
    if area_type:
        sql += " WHERE a.area_type = :area_type"
        params["area_type"] = area_type
    sql += " ORDER BY a.area_type, a.area_name"

    rows = db.execute(text(sql), params).fetchall()
    items = [
        AreaScopeItem(area_id=r[0], area_type=r[1], area_code=r[2], area_name=r[3])
        for r in rows
    ]
    return AreaScopeResponse(data=items, total=len(items))
