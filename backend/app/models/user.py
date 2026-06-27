from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False, comment="로그인 ID")
    hashed_password = Column(String(200), nullable=False, comment="암호화된 비밀번호")
    name = Column(String(100), nullable=False, comment="사용자 이름")
    email = Column(String(100), nullable=False, comment="이메일")
    phone = Column(String(50), nullable=False, comment="연락처")
    
    is_approved = Column(Boolean, default=False, comment="가입 승인 여부")
    is_superuser = Column(Boolean, default=False, comment="관리자(수퍼유저) 여부")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="가입 일시")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="수정 일시")
