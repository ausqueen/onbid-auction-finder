from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional

from ...database import get_db
from ...models.property import Property, AnalysisResult
from ...services.sync_service import get_last_synced_at
from .properties import _serialize_property

from ...models.user import User
from ...models.favorite import UserFavoriteProperty
from ...models.read import UserReadProperty
from .auth import get_current_user

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/top")
def get_top_properties(
    n: int = Query(20, ge=1, le=100, description="추천 물건 수"),
    safe_only: bool = Query(False, description="안전 물건만"),
    sido: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """점수 기준 TOP N 추천 물건"""
    query = db.query(Property).options(
        joinedload(Property.analysis),
        joinedload(Property.market_prices),
    ).join(AnalysisResult, Property.id == AnalysisResult.property_id).filter(
        Property.is_active == True,
        AnalysisResult.gap_pct > 0,
    )

    if safe_only:
        query = query.filter(AnalysisResult.is_safe == True)
    if sido:
        query = query.filter(Property.sido == sido)
    if property_type:
        query = query.filter(Property.property_type == property_type)

    items = query.order_by(AnalysisResult.score.desc()).limit(n).all()

    # 즐겨찾기 목록 조회
    fav_ids = {
        f.property_id for f in db.query(UserFavoriteProperty)
        .filter(UserFavoriteProperty.user_id == current_user.id).all()
    }

    # 읽은 목록 조회
    read_ids = {
        r.property_id for r in db.query(UserReadProperty)
        .filter(UserReadProperty.user_id == current_user.id).all()
    }

    return {
        "count": len(items),
        "items": [_serialize_property(p, p.id in fav_ids, p.id in read_ids) for p in items],
    }


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """전체 통계 요약"""
    total = db.query(Property).filter(Property.is_active == True).count()
    safe_count = db.query(AnalysisResult).filter(AnalysisResult.is_safe == True).count()

    avg_gap = db.query(func.avg(AnalysisResult.gap_pct)).scalar() or 0.0
    top_gap = db.query(func.max(AnalysisResult.gap_pct)).scalar() or 0.0
    avg_score = db.query(func.avg(AnalysisResult.score)).scalar() or 0.0

    # 물건종류별 분포
    type_dist = db.query(
        Property.property_type,
        func.count(Property.id)
    ).filter(Property.is_active == True).group_by(Property.property_type).all()

    # 시도별 분포
    sido_dist = db.query(
        Property.sido,
        func.count(Property.id)
    ).filter(Property.is_active == True).group_by(Property.sido).order_by(
        func.count(Property.id).desc()
    ).limit(10).all()

    return {
        "total_properties": total,
        "safe_properties": safe_count,
        "avg_gap_pct": round(float(avg_gap), 2),
        "top_gap_pct": round(float(top_gap), 2),
        "avg_score": round(float(avg_score), 2),
        "last_synced_at": get_last_synced_at().isoformat() if get_last_synced_at() else None,
        "type_distribution": {row[0]: row[1] for row in type_dist if row[0]},
        "sido_distribution": {row[0]: row[1] for row in sido_dist if row[0]},
    }


@router.get("/gap-distribution")
def get_gap_distribution(db: Session = Depends(get_db)):
    """Gap% 구간별 물건 수 분포 (차트용)"""
    buckets = [
        (0, 10, "0~10%"),
        (10, 20, "10~20%"),
        (20, 30, "20~30%"),
        (30, 40, "30~40%"),
        (40, 50, "40~50%"),
        (50, 100, "50%+"),
    ]

    result = []
    for low, high, label in buckets:
        count = db.query(AnalysisResult).filter(
            AnalysisResult.gap_pct >= low,
            AnalysisResult.gap_pct < high,
        ).count()
        result.append({"label": label, "count": count})

    return {"distribution": result}
