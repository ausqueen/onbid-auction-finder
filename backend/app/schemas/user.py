from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    name: str
    email: str
    phone: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    password: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_approved: Optional[bool] = None
    is_superuser: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_approved: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    name: str
    is_superuser: bool
    is_approved: bool

class TokenData(BaseModel):
    username: Optional[str] = None

class FindIdRequest(BaseModel):
    name: str
    email: str
    phone: str

class FindPasswordRequest(BaseModel):
    username: str
    name: str
    email: str
    phone: str
