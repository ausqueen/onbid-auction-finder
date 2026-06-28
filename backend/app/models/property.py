from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Property(Base):
    """온비드 공매 물건"""
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    notice_no = Column(String(50), unique=True, index=True, comment="공고번호")
    asset_no = Column(String(50), index=True, comment="물건번호")
    address = Column(String(500), nullable=False, comment="소재지(주소)")
    sido = Column(String(20), index=True, comment="시도")
    sigungu = Column(String(30), index=True, comment="시군구")

    property_type = Column(String(30), index=True, comment="물건종류(아파트/토지/상가 등)")
    land_category = Column(String(10), comment="지목(전/답/과수원 등 - 토지의 경우)")
    area_m2 = Column(Float, comment="면적(㎡)")

    appraisal_value = Column(Integer, comment="감정평가액(원)")
    min_bid_price = Column(Integer, comment="최저입찰가(원)")
    fail_count = Column(Integer, default=0, comment="유찰횟수")

    bid_start_dt = Column(DateTime, comment="입찰 시작일시")
    bid_end_dt = Column(DateTime, comment="입찰 종료일시")

    description = Column(Text, comment="물건 상세 설명 / 공고문 내용")
    notice_url = Column(String(500), comment="공고문 URL")
    image_url = Column(String(500), comment="물건 사진 URL")

    is_active = Column(Boolean, default=True, comment="현재 입찰 가능 여부")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    market_prices = relationship("MarketPrice", back_populates="property", cascade="all, delete-orphan")
    analysis = relationship("AnalysisResult", back_populates="property", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_properties_sido_type", "sido", "property_type"),
    )


class MarketPrice(Base):
    """시세 데이터 (국토부 실거래가 등)"""
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    source = Column(String(20), comment="데이터 출처 (molit/naver/kb)")
    price = Column(Integer, comment="시세(원)")
    price_per_m2 = Column(Integer, comment="단위면적당 가격(원/㎡)")
    deal_date = Column(String(10), comment="거래일자(YYYYMM)")
    created_at = Column(DateTime, default=datetime.utcnow)

    property = relationship("Property", back_populates="market_prices")


class AnalysisResult(Base):
    """분석 결과"""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), unique=True, nullable=False)

    # 시세 분석
    market_price = Column(Integer, comment="추정 시세(원)")
    gap_amount = Column(Integer, comment="시세차익(원) = 시세 - 최저입찰가")
    gap_pct = Column(Float, comment="시세차익률(%) = gap_amount / market_price * 100")

    # 세금 추정
    acquisition_tax = Column(Integer, comment="취득세 추정액(원)")

    # 위험 분석
    risk_keywords = Column(Text, comment="감지된 위험 키워드 (JSON 배열)")
    is_blind_land = Column(Boolean, default=False, comment="맹지 여부")
    needs_farm_cert = Column(Boolean, default=False, comment="농취증 필요 여부")
    is_safe = Column(Boolean, default=True, comment="안전 물건 여부 (위험 키워드 없음)")

    # 종합 점수
    score = Column(Float, comment="추천 점수 (높을수록 좋음)")

    # 인수금(보증금) 기능
    tenant_deposit = Column(Integer, default=0, comment="임차인 인수금(원)")

    analyzed_at = Column(DateTime, default=datetime.utcnow)
    property = relationship("Property", back_populates="analysis")
