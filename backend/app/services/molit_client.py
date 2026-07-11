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
from .lawd_codes import resolve_lawd_cd

logger = logging.getLogger(__name__)
settings = get_settings()

# data.go.kr 정상 응답 코드 — 서비스에 따라 "00"/"000"/"0000" 혼재.
# (2026-07: 국토부 실거래가 API가 "000"(OK) 를 반환하여 "00"만 성공 처리하던 기존 로직이
#  전 시세조회를 오류로 흘려버리던 버그 수정. onbid_client 와 동일 정책)
_SUCCESS_CODES = {"00", "000", "0000"}


def _is_success_code(result_code: Optional[str]) -> bool:
    """resultCode 가 없거나(구조 상이) 정상 코드면 True."""
    return (not result_code) or (result_code in _SUCCESS_CODES)


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


def fetch_apt_transactions(lawd_cd: str, deal_ym: str, label: str = "") -> list[dict]:
    """
    아파트 실거래가 조회

    Args:
        lawd_cd: 시군구 5자리 법정동코드 (LAWD_CD, 예: '11680' 강남구)
        deal_ym: 거래년월 (YYYYMM)
        label: 로그용 지역 표기 (예: '서울특별시 강남구')

    Returns:
        거래 정보 dict 리스트
    """
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
        if not _is_success_code(result_code):
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
        logger.info(f"국토부 아파트 실거래 {label or lawd_cd} {deal_ym}: {len(results)}건")
        return results

    except httpx.HTTPError as e:
        logger.error(f"국토부 API HTTP 오류 ({label or lawd_cd}/{deal_ym}): {e}")
        return []
    except ET.ParseError as e:
        logger.error(f"국토부 API XML 파싱 오류: {e}")
        return []


def fetch_land_transactions(lawd_cd: str, deal_ym: str, label: str = "") -> list[dict]:
    """토지 실거래가 조회 (lawd_cd: 시군구 5자리 법정동코드)"""
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
        result_code = root.findtext(".//resultCode")
        if not _is_success_code(result_code):
            logger.error(f"국토부 토지 API 오류: {result_code} - {root.findtext('.//resultMsg')}")
            return []

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
        logger.info(f"국토부 토지 실거래 {label or lawd_cd} {deal_ym}: {len(results)}건")
        return results

    except (httpx.HTTPError, ET.ParseError) as e:
        logger.error(f"국토부 토지 API 오류 ({label or lawd_cd}/{deal_ym}): {e}")
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

    # 시군구 5자리 법정동코드(LAWD_CD) 해석 — 미매칭이면 감정가 기준(None) 처리
    lawd_cds = resolve_lawd_cd(sido, sigungu)
    if not lawd_cds:
        logger.warning(f"LAWD_CD 매핑 실패 — 시세 조회 스킵: {sido} {sigungu or ''}")
        return None

    label = f"{sido} {sigungu}".strip()
    is_land = property_type in ("토지", "농지", "임야")
    deal_months = _get_recent_deal_months(3)
    all_prices = []

    for deal_ym in deal_months:
        for lawd_cd in lawd_cds:
            if is_land:
                transactions = fetch_land_transactions(lawd_cd, deal_ym, label)
            else:
                transactions = fetch_apt_transactions(lawd_cd, deal_ym, label)

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
