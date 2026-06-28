from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
import json

from ...database import get_db
from ...models.property import Property, AnalysisResult
from ...models.user import User
from ...models.favorite import UserFavoriteProperty
from ...models.read import UserReadProperty
from ...schemas.property import PropertyResponse, PropertyListResponse, AnalysisResultSchema
from ...api.endpoints.auth import get_current_user

router = APIRouter(prefix="/properties", tags=["properties"])

@router.get("", response_model=PropertyListResponse)
def list_properties(
    sido: Optional[str] = Query(None, description="시도 필터 (예: 서울, 경기)"),
    property_type: Optional[str] = Query(None, description="물건종류 (예: 아파트, 토지)"),
    min_price: Optional[int] = Query(None, description="최저입찰가 하한(원)"),
    max_price: Optional[int] = Query(None, description="최저입찰가 상한(원)"),
    safe_only: bool = Query(False, description="안전 물건만 보기"),
    min_gap_pct: Optional[float] = Query(None, description="최소 Gap% 필터"),
    min_fail_count: Optional[int] = Query(None, description="최소 유찰횟수"),
    favorites_only: bool = Query(False, description="관심 물건만 보기"),
    unread_only: bool = Query(False, description="미확인 물건만 보기"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """필터링된 공매 물건 목록 조회"""
    # 항상 outerjoin으로 단일 조인 유지 (조건부 inner join + 무조건 outer join 중복 방지)
    query = (
        db.query(Property)
        .options(joinedload(Property.analysis), joinedload(Property.market_prices))
        .outerjoin(AnalysisResult, Property.id == AnalysisResult.property_id)
        .filter(Property.is_active == True)
    )

    if sido:
        query = query.filter(Property.sido == sido)
    if property_type:
        query = query.filter(Property.property_type == property_type)
    if min_price is not None:
        query = query.filter(Property.min_bid_price >= min_price)
    if max_price is not None:
        query = query.filter(Property.min_bid_price <= max_price)
    if min_fail_count is not None:
        query = query.filter(Property.fail_count >= min_fail_count)
    if safe_only:
        query = query.filter(AnalysisResult.is_safe == True)
    if min_gap_pct is not None:
        query = query.filter(AnalysisResult.gap_pct >= min_gap_pct)
    if favorites_only:
        query = query.filter(Property.id.in_(
            db.query(UserFavoriteProperty.property_id).filter(UserFavoriteProperty.user_id == current_user.id)
        ))
    if unread_only:
        query = query.filter(~Property.id.in_(
            db.query(UserReadProperty.property_id).filter(UserReadProperty.user_id == current_user.id)
        ))

    total = query.count()

    # 점수 내림차순 정렬
    query = query.order_by(AnalysisResult.score.desc().nullslast())

    items = query.offset((page - 1) * page_size).limit(page_size).all()

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

    return PropertyListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=_serialize_properties(items, fav_ids, read_ids),
    )


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(
    property_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """물건 상세 조회"""
    prop = db.query(Property).options(
        joinedload(Property.analysis),
        joinedload(Property.market_prices),
    ).filter(Property.id == property_id).first()

    if not prop:
        raise HTTPException(status_code=404, detail="물건을 찾을 수 없습니다")

    is_fav = db.query(UserFavoriteProperty).filter(
        UserFavoriteProperty.user_id == current_user.id,
        UserFavoriteProperty.property_id == property_id
    ).first() is not None

    is_read = db.query(UserReadProperty).filter(
        UserReadProperty.user_id == current_user.id,
        UserReadProperty.property_id == property_id
    ).first() is not None

    return _serialize_property(prop, is_fav, is_read)


@router.get("/regions/list")
def list_regions(db: Session = Depends(get_db)):
    """조회된 지역(시도) 목록"""
    rows = db.query(Property.sido).filter(
        Property.sido != None,
        Property.is_active == True,
    ).distinct().order_by(Property.sido).all()
    return {"regions": [r[0] for r in rows if r[0]]}


@router.get("/types/list")
def list_property_types(db: Session = Depends(get_db)):
    """물건종류 목록"""
    rows = db.query(Property.property_type).filter(
        Property.is_active == True
    ).distinct().order_by(Property.property_type).all()
    return {"types": [r[0] for r in rows if r[0]]}


def _serialize_property(prop: Property, is_favorite: bool = False, is_read: bool = False) -> dict:
    result = {
        "id": prop.id,
        "notice_no": prop.notice_no,
        "address": prop.address,
        "sido": prop.sido,
        "sigungu": prop.sigungu,
        "property_type": prop.property_type,
        "land_category": prop.land_category,
        "area_m2": prop.area_m2,
        "appraisal_value": prop.appraisal_value,
        "min_bid_price": prop.min_bid_price,
        "fail_count": prop.fail_count,
        "bid_start_dt": prop.bid_start_dt,
        "bid_end_dt": prop.bid_end_dt,
        "description": prop.description,
        "notice_url": prop.notice_url,
        "image_url": prop.image_url,
        "is_active": prop.is_active,
        "created_at": prop.created_at,
        "updated_at": prop.updated_at,
        "is_favorite": is_favorite,
        "is_read": is_read,
        "market_prices": [
            {
                "source": mp.source,
                "price": mp.price,
                "price_per_m2": mp.price_per_m2,
                "deal_date": mp.deal_date,
            }
            for mp in (prop.market_prices or [])
        ],
        "analysis": None,
    }

    if prop.analysis:
        a = prop.analysis
        result["analysis"] = {
            "market_price": a.market_price,
            "gap_amount": a.gap_amount,
            "gap_pct": a.gap_pct,
            "acquisition_tax": a.acquisition_tax,
            "risk_keywords": json.loads(a.risk_keywords) if a.risk_keywords else [],
            "is_blind_land": a.is_blind_land,
            "needs_farm_cert": a.needs_farm_cert,
            "is_safe": a.is_safe,
            "score": a.score,
            "analyzed_at": a.analyzed_at,
        }
    return result


def _serialize_properties(props: list, fav_ids: set = None, read_ids: set = None) -> list:
    if fav_ids is None:
        fav_ids = set()
    if read_ids is None:
        read_ids = set()
    return [_serialize_property(p, p.id in fav_ids, p.id in read_ids) for p in props]


@router.post("/{property_id}/read", response_model=dict)
def mark_property_as_read(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """물건을 읽음 상태로 표시"""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="물건을 찾을 수 없습니다.")

    existing = db.query(UserReadProperty).filter(
        UserReadProperty.user_id == current_user.id,
        UserReadProperty.property_id == property_id
    ).first()

    if not existing:
        read_record = UserReadProperty(user_id=current_user.id, property_id=property_id)
        db.add(read_record)
        db.commit()

    return {"message": "읽음 상태로 표시되었습니다.", "is_read": True}


@router.delete("/{property_id}/read", response_model=dict)
def mark_property_as_unread(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """물건을 안읽음 상태로 표시"""
    read_record = db.query(UserReadProperty).filter(
        UserReadProperty.user_id == current_user.id,
        UserReadProperty.property_id == property_id
    ).first()

    if read_record:
        db.delete(read_record)
        db.commit()

    return {"message": "안읽음 상태로 표시되었습니다.", "is_read": False}



