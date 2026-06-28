from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
import json


class MarketPriceSchema(BaseModel):
    source: str
    price: int
    price_per_m2: Optional[int] = None
    deal_date: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisResultSchema(BaseModel):
    market_price: Optional[int] = None
    gap_amount: Optional[int] = None
    gap_pct: Optional[float] = None
    acquisition_tax: Optional[int] = None
    risk_keywords: List[str] = []
    is_blind_land: bool = False
    needs_farm_cert: bool = False
    is_safe: bool = True
    score: Optional[float] = None
    tenant_deposit: Optional[int] = None
    analyzed_at: Optional[datetime] = None

    @classmethod
    def from_orm_with_json(cls, obj):
        data = {
            "market_price": obj.market_price,
            "gap_amount": obj.gap_amount,
            "gap_pct": obj.gap_pct,
            "acquisition_tax": obj.acquisition_tax,
            "risk_keywords": json.loads(obj.risk_keywords) if obj.risk_keywords else [],
            "is_blind_land": obj.is_blind_land,
            "needs_farm_cert": obj.needs_farm_cert,
            "is_safe": obj.is_safe,
            "score": obj.score,
            "tenant_deposit": obj.tenant_deposit,
            "analyzed_at": obj.analyzed_at,
        }
        return cls(**data)

    class Config:
        from_attributes = True


class PropertyBase(BaseModel):
    notice_no: str
    address: str
    sido: Optional[str] = None
    sigungu: Optional[str] = None
    property_type: str
    land_category: Optional[str] = None
    area_m2: Optional[float] = None
    appraisal_value: Optional[int] = None
    min_bid_price: int
    fail_count: int = 0
    bid_start_dt: Optional[datetime] = None
    bid_end_dt: Optional[datetime] = None
    description: Optional[str] = None
    notice_url: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True


class PropertyCreate(PropertyBase):
    pass


class PropertyResponse(PropertyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    analysis: Optional[AnalysisResultSchema] = None
    market_prices: List[MarketPriceSchema] = []
    is_favorite: Optional[bool] = False
    is_read: Optional[bool] = False

    class Config:
        from_attributes = True


class PropertyListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[PropertyResponse]


class SummaryResponse(BaseModel):
    total_properties: int
    safe_properties: int
    avg_gap_pct: float
    top_gap_pct: float
    last_synced_at: Optional[datetime] = None


# 필터 쿼리 파라미터용
class PropertyFilter(BaseModel):
    sido: Optional[str] = None
    property_type: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    safe_only: bool = False
    min_gap_pct: Optional[float] = None
    min_fail_count: Optional[int] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
