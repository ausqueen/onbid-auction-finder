import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, FindIdRequest, FindPasswordRequest
import random
import string

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login-oauth2", auto_error=False)

# ── 비밀번호 보안 헬퍼 ──────────────────────────────
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# ── JWT 토큰 생성 및 검증 ───────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 토큰이 유효하지 않거나 만료되었습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
        
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자의 승인이 대기 중인 계정입니다. 승인 후 로그인해 주세요."
        )
    return user

async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user

# ── API 엔드포인트 ─────────────────────────────────

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # 중복 확인
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 아이디입니다."
        )
    
    # 비밀번호 최소 강도 체크 (옵션)
    if len(user_in.password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호는 최소 4자 이상이어야 합니다."
        )

    # 유저 생성 (초기값: 승인대기 false, 수퍼유저 false)
    db_user = User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        name=user_in.name,
        email=user_in.email,
        phone=user_in.phone,
        is_approved=False,
        is_superuser=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# JSON 방식의 로그인
@router.post("/login", response_model=Token)
def login_json(user_info: dict, db: Session = Depends(get_db)):
    username = user_info.get("username")
    password = user_info.get("password")
    
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="아이디와 비밀번호를 모두 입력해 주세요."
        )
        
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다."
        )
        
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자의 가입 승인이 완료되지 않았습니다. 승인 완료 후 이용하실 수 있습니다."
        )
        
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "name": user.name,
        "is_superuser": user.is_superuser,
        "is_approved": user.is_approved
    }

# OAuth2 호환을 위한 엔드포인트 (FastAPI Swagger UI 등에서 테스트용)
from fastapi.security import OAuth2PasswordRequestForm
@router.post("/login-oauth2")
def login_oauth2(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="아이디 또는 비밀번호가 틀렸습니다.")
    if not user.is_approved:
        raise HTTPException(status_code=400, detail="승인되지 않은 계정입니다.")
        
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/find-id")
def find_id(req: FindIdRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.name == req.name,
        User.email == req.email,
        User.phone == req.phone
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="입력하신 정보와 일치하는 가입 정보를 찾을 수 없습니다."
        )
    return {"username": user.username}

@router.post("/find-password")
def find_password(req: FindPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.username == req.username,
        User.name == req.name,
        User.email == req.email,
        User.phone == req.phone
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="입력하신 정보와 일치하는 가입 정보를 찾을 수 없습니다."
        )
        
    # 임시 비밀번호 생성 (8자리 영문/숫자 혼합)
    chars = string.ascii_letters + string.digits
    temp_password = "".join(random.choice(chars) for _ in range(8))
    
    # 임시 비밀번호 저장
    user.hashed_password = get_password_hash(temp_password)
    db.commit()
    
    return {
        "message": "임시 비밀번호가 발급되었습니다. 로그인 후 비밀번호를 변경해 주세요.",
        "temp_password": temp_password
    }
