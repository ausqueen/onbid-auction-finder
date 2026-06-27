from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.api.endpoints.auth import get_current_superuser, get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db), 
    current_admin: User = Depends(get_current_superuser)
):
    """
    모든 가입 유저 목록을 반환합니다 (관리자 전용).
    최신 가입 순으로 정렬합니다.
    """
    return db.query(User).order_by(User.created_at.desc()).all()

@router.post("/users/{user_id}/approve", response_model=UserResponse)
def approve_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_admin: User = Depends(get_current_superuser)
):
    """
    대기 중인 회원을 승인합니다.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다.")
        
    user.is_approved = True
    db.commit()
    db.refresh(user)
    return user

@router.post("/users/{user_id}/reject")
def reject_user(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_admin: User = Depends(get_current_superuser)
):
    """
    회원을 거절(삭제)하거나 탈퇴 처리합니다.
    자기 자신은 거절할 수 없습니다.
    """
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="자기 자신의 계정은 거절/삭제할 수 없습니다.")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다.")
        
    # 만약 root 계정을 삭제하려는 경우 차단
    if user.username == "root":
        raise HTTPException(status_code=400, detail="root 관리자 계정은 삭제할 수 없습니다.")
        
    db.delete(user)
    db.commit()
    return {"message": "사용자가 반려/삭제되었습니다."}

@router.post("/users/{user_id}/toggle-superuser", response_model=UserResponse)
def toggle_superuser(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_admin: User = Depends(get_current_superuser)
):
    """
    사용자의 관리자 권한을 토글합니다 (일반유저 <-> 관리자).
    자기 자신의 관리자 권한은 해제할 수 없으며, root 계정의 관리자 권한은 해제할 수 없습니다.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다.")
        
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="자기 자신의 관리자 권한은 해제할 수 없습니다.")
        
    if user.username == "root":
        raise HTTPException(status_code=400, detail="root 계정의 관리자 권한은 해제할 수 없습니다.")
        
    # 승인되지 않은 회원에게는 권한 부여 불가
    if not user.is_approved:
        raise HTTPException(status_code=400, detail="승인 완료되지 않은 회원에게 관리자 권한을 부여할 수 없습니다.")
        
    user.is_superuser = not user.is_superuser
    db.commit()
    db.refresh(user)
    return user
