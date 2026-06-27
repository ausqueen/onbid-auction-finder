from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import get_db
from app.models.user import User
from app.models.favorite import UserFavoriteProperty, UserFavoriteBankruptcy
from app.models.property import Property
from app.models.bankruptcy import BankruptcyProperty
from app.schemas.user import UserResponse
from app.api.endpoints.auth import get_current_user, get_password_hash, verify_password

router = APIRouter(prefix="/users", tags=["users"])

# ── 1. 프로필 관리 ───────────────────────────────────

@router.put("/me/profile", response_model=UserResponse)
def update_profile(
    profile_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    name = profile_data.get("name")
    email = profile_data.get("email")
    phone = profile_data.get("phone")

    if not name or not email or not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이름, 이메일, 연락처는 필수 입력 값입니다."
        )

    current_user.name = name
    current_user.email = email
    current_user.phone = phone
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/me/change-password")
def change_password(
    password_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_password = password_data.get("current_password")
    new_password = password_data.get("new_password")

    if not current_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호와 새 비밀번호를 모두 입력해주세요."
        )

    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다."
        )

    if len(new_password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="새 비밀번호는 최소 4자 이상이어야 합니다."
        )

    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}

# ── 2. 온비드 공매 관심물건 ─────────────────────────

@router.get("/me/favorites/properties")
def get_favorite_properties(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 유저의 즐겨찾기를 조인하여 실제 Property 정보 반환
    favorites = db.query(Property).join(
        UserFavoriteProperty, Property.id == UserFavoriteProperty.property_id
    ).filter(UserFavoriteProperty.user_id == current_user.id).all()
    
    # 리스트에서 반환할 때 is_favorite=True 하드코딩 주입
    result = []
    for item in favorites:
        # dict 변환하여 is_favorite 추가
        d = {c.name: getattr(item, c.name) for c in item.__table__.columns}
        d["is_favorite"] = True
        result.append(d)
    return result

@router.post("/me/favorites/properties/{property_id}")
def add_favorite_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 물건 존재 여부 확인
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="물건을 찾을 수 없습니다.")

    # 이미 즐겨찾기 되어 있는지 확인
    existing = db.query(UserFavoriteProperty).filter(
        UserFavoriteProperty.user_id == current_user.id,
        UserFavoriteProperty.property_id == property_id
    ).first()
    
    if existing:
        return {"message": "이미 관심물건으로 등록되어 있습니다."}

    fav = UserFavoriteProperty(user_id=current_user.id, property_id=property_id)
    db.add(fav)
    db.commit()
    return {"message": "관심물건으로 등록되었습니다.", "is_favorite": True}

@router.delete("/me/favorites/properties/{property_id}")
def remove_favorite_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fav = db.query(UserFavoriteProperty).filter(
        UserFavoriteProperty.user_id == current_user.id,
        UserFavoriteProperty.property_id == property_id
    ).first()

    if not fav:
        raise HTTPException(status_code=404, detail="관심물건 등록 내역이 없습니다.")

    db.delete(fav)
    db.commit()
    return {"message": "관심물건 등록이 해제되었습니다.", "is_favorite": False}

# ── 3. 법원 파산 관심물건 ───────────────────────────

@router.get("/me/favorites/bankruptcy")
def get_favorite_bankruptcies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    favorites = db.query(BankruptcyProperty).join(
        UserFavoriteBankruptcy, BankruptcyProperty.id == UserFavoriteBankruptcy.bankruptcy_id
    ).filter(UserFavoriteBankruptcy.user_id == current_user.id).all()
    
    result = []
    for item in favorites:
        d = {c.name: getattr(item, c.name) for c in item.__table__.columns}
        d["is_favorite"] = True
        result.append(d)
    return result

@router.post("/me/favorites/bankruptcy/{bankruptcy_id}")
def add_favorite_bankruptcy(
    bankruptcy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bp = db.query(BankruptcyProperty).filter(BankruptcyProperty.id == bankruptcy_id).first()
    if not bp:
        raise HTTPException(status_code=404, detail="파산 물건을 찾을 수 없습니다.")

    existing = db.query(UserFavoriteBankruptcy).filter(
        UserFavoriteBankruptcy.user_id == current_user.id,
        UserFavoriteBankruptcy.bankruptcy_id == bankruptcy_id
    ).first()
    
    if existing:
        return {"message": "이미 관심물건으로 등록되어 있습니다."}

    fav = UserFavoriteBankruptcy(user_id=current_user.id, bankruptcy_id=bankruptcy_id)
    db.add(fav)
    db.commit()
    return {"message": "관심물건으로 등록되었습니다.", "is_favorite": True}

@router.delete("/me/favorites/bankruptcy/{bankruptcy_id}")
def remove_favorite_bankruptcy(
    bankruptcy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fav = db.query(UserFavoriteBankruptcy).filter(
        UserFavoriteBankruptcy.user_id == current_user.id,
        UserFavoriteBankruptcy.bankruptcy_id == bankruptcy_id
    ).first()

    if not fav:
        raise HTTPException(status_code=404, detail="관심물건 등록 내역이 없습니다.")

    db.delete(fav)
    db.commit()
    return {"message": "관심물건 등록이 해제되었습니다.", "is_favorite": False}
