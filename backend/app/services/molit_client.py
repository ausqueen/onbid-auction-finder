"""
국토교통부 실거래가 API 클라이언트
공공데이터포털 국토부 부동산 실거래가 정보

문서: https://www.data.go.kr/data/15057511/openapi.do
"""

import httpx
import logging
from datetime import datetime
from typing import Optional
from xml.etree import ElementTree as ET

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 시도별 법정동 코드 앞 5자리 (광역시/도)
SIDO_LAWD_CD = {
    "서울": "11",
    "부산": "26",
    "대구": "27",
    "인천": "28",
    "광주": "29",
    "대전": "30",
    "울산": "31",
    "세종": "36",
    "경기": "41",
    "강원": "42",
    "충북": "43",
    "충남": "44",
    "전북": "45",
    "전남": "46",
    "경북": "47",
    "경남": "48",
    "제주": "50",
}


def _parse_int(value: str) -> Optional[int]:
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _parse_float(value: str) -> Optional[float]:
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _price_to_won(price_str: str) -> Optional[int]:
    """실거래가 문자열 '10,000' (만원 단위) → 원 단위 변환"""
    try:
        price_str = str(price_str).replace(",", "").strip()
        return int(float(price_str) * 10_000)
    except (ValueError, TypeError):
        return None


def _get_recent_deal_months(n: int = 3) -> list[str]:
    """최근 n개월의 YYYYMM 문자열 리스트 반환"""
    from datetime import date
    import calendar
    result = []
    today = date.today()
    for i in range(n):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        result.append(f"{year}{month:02d}")
    return result


def fetch_apt_transactions(sido: str, deal_ym: str) -> list[dict]:
    """
    아파트 실거래가 조회

    Args:
        sido: 시도명 (예: '서울', '경기')
        deal_ym: 거래년월 (YYYYMM)

    Returns:
        거래 정보 dict 리스트
    """
    lawd_prefix = SIDO_LAWD_CD.get(sido)
    if not lawd_prefix:
        logger.warning(f"지원하지 않는 시도: {sido}")
        return []

    # 국토부는 시군구 단위(5자리) 필요 - 시도 코드로 10000 단위 조회
    lawd_cd = lawd_prefix + "000"

    url = f"{settings.molit_base_url}/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
    params = {
        "serviceKey": settings.molit_api_key,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ym,
        "numOfRows": 1000,
        "pageNo": 1,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

        root = ET.fromstring(response.text)
        result_code = root.findtext(".//resultCode")
        if result_code and result_code != "00":
            logger.error(f"국토부 API 오류: {result_code} - {root.findtext('.//resultMsg')}")
            return []

        items = root.findall(".//item")
        results = []
        for item in items:
            def get(tag: str) -> str:
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else ""

            price_won = _price_to_won(get("dealAmount"))
            area = _parse_float(get("excluUseAr"))  # 전용면적
            if price_won and area:
                results.append({
                    "source": "molit",
                    "address": f"{get('umdNm')} {get('jibun')}",
                    "apt_name": get("aptNm"),
                    "area_m2": area,
                    "price": price_won,
                    "price_per_m2": int(price_won / area) if area > 0 else None,
                    "floor": get("floor"),
                    "deal_date": f"{get('dealYear')}{get('dealMonth').zfill(2)}",
                })
        logger.info(f"국토부 아파트 실거래 {sido} {deal_ym}: {len(results)}건")
        return results

    except httpx.HTTPError as e:
        logger.error(f"국토부 API HTTP 오류 ({sido}/{deal_ym}): {e}")
        return []
    except ET.ParseError as e:
        logger.error(f"국토부 API XML 파싱 오류: {e}")
        return []


def fetch_land_transactions(sido: str, deal_ym: str) -> list[dict]:
    """토지 실거래가 조회"""
    lawd_prefix = SIDO_LAWD_CD.get(sido)
    if not lawd_prefix:
        return []

    lawd_cd = lawd_prefix + "000"
    url = f"{settings.molit_base_url}/RTMSDataSvcLandTrade/getRTMSDataSvcLandTrade"
    params = {
        "serviceKey": settings.molit_api_key,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ym,
        "numOfRows": 1000,
        "pageNo": 1,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

        root = ET.fromstring(response.text)
        items = root.findall(".//item")
        results = []
        for item in items:
            def get(tag: str) -> str:
                el = item.find(tag)
                return el.text.strip() if el is not None and el.text else ""

            price_won = _price_to_won(get("dealAmount"))
            area = _parse_float(get("area"))
            if price_won:
                results.append({
                    "source": "molit",
                    "address": f"{get('umdNm')} {get('jibun')}",
                    "area_m2": area,
                    "price": price_won,
                    "price_per_m2": int(price_won / area) if area and area > 0 else None,
                    "land_type": get("landType"),
                    "deal_date": f"{get('dealYear')}{get('dealMonth').zfill(2)}",
                })
        logger.info(f"국토부 토지 실거래 {sido} {deal_ym}: {len(results)}건")
        return results

    except (httpx.HTTPError, ET.ParseError) as e:
        logger.error(f"국토부 토지 API 오류 ({sido}/{deal_ym}): {e}")
        return []


def get_market_price_estimate(
    sido: str,
    property_type: str,
    area_m2: float,
    sigungu: Optional[str] = None,
) -> Optional[int]:
    """
    실거래가 기반 시세 추정

    최근 3개월 동일 지역 유사 면적 물건의 중앙값 반환
    API 키 없으면 감정평가액 기반 추정 반환 (None)
    """
    if not settings.molit_api_key:
        return None  # 키 없으면 price_analyzer에서 감정가 기준으로 처리

    deal_months = _get_recent_deal_months(3)
    all_prices = []

    for deal_ym in deal_months:
        if property_type in ("아파트", "오피스텔", "빌라/연립"):
            transactions = fetch_apt_transactions(sido, deal_ym)
        elif property_type in ("토지", "농지", "임야"):
            transactions = fetch_land_transactions(sido, deal_ym)
        else:
            transactions = fetch_apt_transactions(sido, deal_ym)

        # 면적 ±20% 범위 필터
        for t in transactions:
            t_area = t.get("area_m2") or 0
            if area_m2 and t_area:
                if abs(t_area - area_m2) / area_m2 <= 0.2:
                    all_prices.append(t["price"])
            elif t.get("price"):
                all_prices.append(t["price"])

    if not all_prices:
        return None

    # 중앙값 반환
    all_prices.sort()
    mid = len(all_prices) // 2
    return all_prices[mid]
