from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BankruptcyPropertyBase(BaseModel):
    title: str
    board_no: Optional[int] = None       # 공고게시판 번호 (446, 445...)
    post_date: Optional[str] = None      # 문자열 날짜 (예: "2026-04-21")
    court_name: Optional[str] = None
    notice_url: str

class BankruptcyPropertyCreate(BankruptcyPropertyBase):
    pass

class BankruptcyPropertyUpdate(BaseModel):
    asset_type: Optional[str] = None
    target_property: Optional[str] = None
    address: Optional[str] = None
    min_price: Optional[str] = None
    manager_contact: Optional[str] = None
    sale_deadline: Optional[str] = None
    ai_summary: Optional[str] = None
    is_recommended: Optional[bool] = False
    is_analyzed: Optional[bool] = False

class BankruptcyPropertyResponse(BankruptcyPropertyBase):
    id: int
    asset_type: Optional[str] = None
    target_property: Optional[str] = None
    address: Optional[str] = None
    min_price: Optional[str] = None
    manager_contact: Optional[str] = None
    sale_deadline: Optional[str] = None
    ai_summary: Optional[str] = None
    is_recommended: Optional[bool] = False
    is_analyzed: Optional[bool] = False
    # 상세 페이지 파싱 메타데이터
    selling_agency: Optional[str] = None
    phone_number: Optional[str] = None
    attachment_filename: Optional[str] = None
    attachments: Optional[list] = None
    notice_expire_date: Optional[str] = None
    is_favorite: Optional[bool] = False
    is_read: Optional[bool] = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
