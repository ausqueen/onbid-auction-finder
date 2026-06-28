from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.database import Base

class BankruptcyProperty(Base):
    __tablename__ = "bankruptcy_properties"

    id = Column(Integer, primary_key=True, index=True)
    board_no = Column(Integer, nullable=True, index=True, comment="공고게시판 번호 (446, 445...)")
    post_date = Column(String(30), nullable=True, comment="공고일 (문자열)")
    title = Column(String(500), nullable=False, comment="공고 제목")
    court_name = Column(String(100), nullable=True, comment="법원명")
    notice_url = Column(String(500), nullable=False, unique=True, comment="대법원 상세 공고 URL")

    # 공고 상세 페이지에서 파싱한 메타데이터
    selling_agency = Column(String(500), nullable=True, comment="매각기관 (파산관재인 전체 명칭)")
    phone_number = Column(String(100), nullable=True, comment="전화번호")
    attachment_filename = Column(String(500), nullable=True, comment="첨부파일 파일명 (확장자 포함)")
    attachments = Column(JSON, nullable=True, comment="첨부파일 리스트 JSON (파일명, 로컬파일명 등)")
    notice_expire_date = Column(String(30), nullable=True, comment="공고만료일")

    # Gemini API 추출 데이터
    asset_type = Column(String(50), nullable=True, comment="물건 종류 (부동산/유체동산/채권/기타)")
    target_property = Column(Text, nullable=True, comment="매각 대상 물건")
    address = Column(String(500), nullable=True, comment="추출된 물건지 주소 (도로명/지번)")
    min_price = Column(String(200), nullable=True, comment="최저 매각 가격")
    manager_contact = Column(String(200), nullable=True, comment="파산관재인 연락처")
    sale_deadline = Column(String(200), nullable=True, comment="매각기일/마감일")
    
    # 원문 요약 (또는 기타 정보)
    ai_summary = Column(Text, nullable=True, comment="Gemini 자동 요약")
    is_recommended = Column(Boolean, default=False, comment="추천 물건 여부")

    # Phase 관리: False = 기본정보만 수집됨, True = AI 분석 완료
    is_analyzed = Column(Boolean, default=False, comment="Gemini AI 분석 완료 여부")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
