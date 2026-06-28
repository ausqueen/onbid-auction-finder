"""
온비드(OnBid) OpenAPI 클라이언트
차세대 온비드 부동산 물건 목록/상세 조회서비스 V2

목록: https://apis.data.go.kr/B010003/OnbidRlstListSrvc2/getRlstCltrList2
상세: https://apis.data.go.kr/B010003/OnbidRlstDtlSrvc2/getRlstDtlInf2
"""

import time
import httpx
import logging
from datetime import datetime
from typing import Optional
from xml.etree import ElementTree as ET

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 물건종류 코드 매핑 (온비드 prdClUp 코드)
PROPERTY_TYPE_MAP = {
    "0001": "아파트",
    "0002": "빌라/연립",
    "0003": "단독/다가구",
    "0004": "오피스텔",
    "0010": "토지",
    "0020": "상가",
    "0030": "공장/창고",
    "0040": "농지",
    "0050": "임야",
    "0099": "기타",
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


def _parse_datetime(value: str) -> Optional[datetime]:
    """온비드 날짜 형식 파싱 (YYYYMMDDHHMMSS 또는 YYYYMMDD)"""
    if not value:
        return None
    try:
        value = str(value).strip()
        if len(value) >= 14:
            return datetime.strptime(value[:14], "%Y%m%d%H%M%S")
        elif len(value) == 8:
            return datetime.strptime(value[:8], "%Y%m%d")
        return None
    except ValueError:
        return None


def _extract_sido(address: str) -> str:
    """주소에서 시도 추출"""
    prefixes = [
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"
    ]
    for prefix in prefixes:
        if address.startswith(prefix):
            return prefix
    return address.split()[0] if address else "기타"


def _extract_sigungu(address: str) -> str:
    """주소에서 시군구 추출"""
    parts = address.split()
    if len(parts) >= 2:
        return parts[1]
    return ""


def _parse_item_json(item: dict) -> Optional[dict]:
    """JSON 응답 item을 dict로 파싱 (구버전 호환용)"""
    def g(key: str) -> str:
        return str(item.get(key, "") or "").strip()

    notice_no = g("plnbNo") or g("pblancNo") or g("gdNo")
    address = g("ldnm") or g("addr") or g("roadAdres") or g("jibunAdres")
    if not notice_no or not address:
        return None

    property_type_code = g("prdClUp")
    property_type = PROPERTY_TYPE_MAP.get(property_type_code, g("prdClUpNm") or "기타")
    appraisal_raw = g("apprsAmt") or g("apprslAmt") or g("apprAmt")
    min_bid_raw = g("lstBdPrc") or g("minBdPrc") or g("minlmprc")
    area_raw = g("totArea") or g("splyArea") or g("area") or g("pcbArea")
    fail_raw = g("nrmlFlrCnt") or g("flrCnt") or g("failCnt")

    return {
        "notice_no": notice_no,
        "asset_no": g("assetNo") or g("gdNo"),
        "address": address,
        "sido": _extract_sido(address),
        "sigungu": _extract_sigungu(address),
        "property_type": property_type,
        "land_category": g("ldCd") or g("jimok"),
        "area_m2": _parse_float(area_raw),
        "appraisal_value": _parse_int(appraisal_raw),
        "min_bid_price": _parse_int(min_bid_raw) or 0,
        "fail_count": _parse_int(fail_raw) or 0,
        "bid_start_dt": _parse_datetime(g("bidBeginDt") or g("bidStrtDt")),
        "bid_end_dt": _parse_datetime(g("bidEndDt")),
        "description": g("rmk") or g("specl") or g("bidNtcCn"),
        "notice_url": g("detailUrl") or f"https://www.onbid.co.kr/op/psa/selectPbsoDetail.do?pblancNo={notice_no}",
        "image_url": g("imgPath") or None,
        "is_active": True,
    }


def _parse_item(item: ET.Element) -> Optional[dict]:
    """XML item 요소를 dict로 파싱 (차세대 V2 API 필드)"""
    def get(tag: str) -> str:
        el = item.find(tag)
        return el.text.strip() if el is not None and el.text else ""

    notice_no = get("cltrMngNo")  # 차세대 물건관리번호
    if not notice_no:
        return None

    address = f"{get('lctnSdnm')} {get('lctnSggnm')} {get('lctnEmdNm')}".strip()
    property_type = get("cltrUsgSclsCtgrNm") or get("prptDivNm") or "기타"

    appraisal_raw = get("apslEvlAmt")
    min_bid_raw = get("lowstBidPrcIndctCont")
    fail_raw = get("usbdNft")

    bld_sqms = _parse_float(get("bldSqms")) or 0.0
    land_sqms = _parse_float(get("landSqms")) or 0.0
    area_m2 = bld_sqms if bld_sqms > 0 else land_sqms

    bid_start = _parse_datetime(get("cltrBidBgngDt"))
    bid_end = _parse_datetime(get("cltrBidEndDt"))
    image_url = get("thnlImgUrlAdr") or None

    return {
        "notice_no": notice_no,
        "asset_no": get("onbidCltrno") or get("pbctNo"),
        "address": address if address else "소재지 미상",
        "sido": get("lctnSdnm") or _extract_sido(address),
        "sigungu": get("lctnSggnm") or _extract_sigungu(address),
        "property_type": property_type,
        "land_category": None,       # 상세 조회에서 채움
        "area_m2": area_m2,
        "appraisal_value": _parse_int(appraisal_raw),
        "min_bid_price": _parse_int(min_bid_raw) or 0,
        "fail_count": _parse_int(fail_raw) or 0,
        "bid_start_dt": bid_start,
        "bid_end_dt": bid_end,
        "description": get("onbidCltrNm"),  # 목록에서는 물건명. 상세 조회로 보완
        "notice_url": "https://www.onbid.co.kr/",
        "image_url": image_url,
        "is_active": True,
    }


def fetch_properties(
    page_no: int = 1,
    num_of_rows: int = 100,
    property_type_code: Optional[str] = None,
) -> list[dict]:
    """차세대 온비드 공매물건 목록 조회 V2 (OnbidRlstListSrvc2)"""
    url = f"{settings.onbid_base_url}/OnbidRlstListSrvc2/getRlstCltrList2"
    params = {
        "serviceKey": settings.onbid_api_key,
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "resultType": "xml",
        "prptDivCd": property_type_code or "0007,0005,0010,0002",
        "pvctTrgtYn": "N",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

        logger.info(f"온비드 API 응답 RAW (처음 500자): {response.text[:500]}")

        # XML 파싱 (resultType=xml 고정)
        root = ET.fromstring(response.text)
        result_code = root.findtext(".//resultCode") or root.findtext(".//errCode")
        if result_code and result_code != "00" and result_code != "0000":
            result_msg = root.findtext(".//resultMsg") or root.findtext(".//errMsg")
            logger.error(f"온비드 API 오류: {result_code} - {result_msg}")
            return []

        items = root.findall(".//item")
        logger.info(f"온비드 API 응답: 페이지 {page_no}, {len(items)}건")

        results = []
        for item in items:
            parsed = _parse_item(item)
            if parsed:
                results.append(parsed)
        return results

    except httpx.HTTPError as e:
        logger.error(f"온비드 목록 API HTTP 오류: {e}")
        return []
    except ET.ParseError as e:
        logger.error(f"온비드 목록 API XML 파싱 오류: {e}")
        return []


def fetch_property_detail(notice_no: str) -> dict:
    """온비드 물건 상세 조회 V2 (OnbidRlstDtlSrvc2) - cltrMngNo 필수"""
    url = f"{settings.onbid_base_url}/OnbidRlstDtlSrvc2/getRlstDtlInf2"
    params = {
        "serviceKey": settings.onbid_api_key,
        "cltrMngNo": notice_no,
        "resultType": "xml",
    }

    result = {"description": "", "land_category": None, "image_url": None}
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()

        root = ET.fromstring(response.text)
        result_code = root.findtext(".//resultCode")
        if result_code and result_code != "00":
            return result

        item = root.find(".//item")
        if item is None:
            return result

        def get(tag: str) -> str:
            el = item.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        desc_parts = []
        etc_cont = get("cltrEtcCont")
        if etc_cont:
            desc_parts.append(f"[기타사항]\n{etc_cont}")
        pytn_cont = get("pytnMtrsCont")
        if pytn_cont:
            desc_parts.append(f"[유의사항]\n{pytn_cont}")
        evc_cont = get("evcRsbyTrgtCont")
        if evc_cont:
            desc_parts.append(f"[인도인수책임]\n{evc_cont}")

        result["description"] = "\n\n".join(desc_parts)

        cland_cont = root.findtext(".//clandCont")
        if cland_cont:
            result["land_category"] = cland_cont.split(">")[-1]

        poto_url = root.findtext(".//urlAdr")
        if poto_url:
            result["image_url"] = poto_url

    except Exception as e:
        logger.error(f"온비드 상세 조회 오류 {notice_no}: {e}")

    return result


def fetch_all_properties(max_pages: int = 10) -> list[dict]:
    """
    온비드 공매물건 전체 조회 (페이지네이션)
    API 키가 없는 경우 목업 데이터 반환
    """
    if not settings.onbid_api_key:
        logger.warning("온비드 API 키 미설정 - 목업 데이터 사용")
        return _get_mock_properties()

    all_items = []
    for page in range(1, max_pages + 1):
        items = fetch_properties(page_no=page)
        if not items:
            logger.info(f"온비드 API: 페이지 {page}에서 데이터 없음, 수집 종료")
            break
        all_items.extend(items)
        logger.info(f"온비드 수집 누계: {len(all_items)}건 (페이지 {page}/{max_pages})")
        time.sleep(0.5)  # 공공 API 서버 부하 방지 딜레이

    logger.info(f"온비드 전체 수집 완료: {len(all_items)}건")
    return all_items


def _get_mock_properties() -> list[dict]:
    """API 키 없을 때 사용하는 목업 데이터 (개발/테스트용)"""
    from datetime import timedelta
    now = datetime.now()

    return [
        {
            "notice_no": "2024-001", "asset_no": "A001",
            "address": "서울 강남구 역삼동 123-45", "sido": "서울", "sigungu": "강남구",
            "property_type": "아파트", "land_category": None, "area_m2": 84.0,
            "appraisal_value": 1_200_000_000, "min_bid_price": 720_000_000, "fail_count": 3,
            "bid_start_dt": now, "bid_end_dt": now + timedelta(days=7),
            "description": "역삼동 소재 아파트, 임차인 대항력 없음",
            "notice_url": "https://www.onbid.co.kr/", "image_url": None, "is_active": True,
        },
        {
            "notice_no": "2024-002", "asset_no": "A002",
            "address": "경기 수원시 영통구 영통동 456-78", "sido": "경기", "sigungu": "수원시",
            "property_type": "아파트", "land_category": None, "area_m2": 59.0,
            "appraisal_value": 500_000_000, "min_bid_price": 250_000_000, "fail_count": 5,
            "bid_start_dt": now, "bid_end_dt": now + timedelta(days=7),
            "description": "영통동 소재 아파트",
            "notice_url": "https://www.onbid.co.kr/", "image_url": None, "is_active": True,
        },
        {
            "notice_no": "2024-003", "asset_no": "A003",
            "address": "전남 나주시 빛가람동 789", "sido": "전남", "sigungu": "나주시",
            "property_type": "토지", "land_category": "답", "area_m2": 3000.0,
            "appraisal_value": 150_000_000, "min_bid_price": 60_000_000, "fail_count": 2,
            "bid_start_dt": now, "bid_end_dt": now + timedelta(days=7),
            "description": "나주시 소재 농지(답). 농취증 필요.",
            "notice_url": "https://www.onbid.co.kr/", "image_url": None, "is_active": True,
        },
        {
            "notice_no": "2024-004", "asset_no": "A004",
            "address": "부산 해운대구 우동 123", "sido": "부산", "sigungu": "해운대구",
            "property_type": "상가", "land_category": None, "area_m2": 45.0,
            "appraisal_value": 300_000_000, "min_bid_price": 120_000_000, "fail_count": 4,
            "bid_start_dt": now, "bid_end_dt": now + timedelta(days=7),
            "description": "해운대 소재 상가. 유치권 신고 있음.",
            "notice_url": "https://www.onbid.co.kr/", "image_url": None, "is_active": True,
        },
        {
            "notice_no": "2024-005", "asset_no": "A005",
            "address": "인천 연수구 송도동 99-1", "sido": "인천", "sigungu": "연수구",
            "property_type": "오피스텔", "land_category": None, "area_m2": 33.0,
            "appraisal_value": 250_000_000, "min_bid_price": 125_000_000, "fail_count": 3,
            "bid_start_dt": now, "bid_end_dt": now + timedelta(days=7),
            "description": "송도 소재 오피스텔, 공실",
            "notice_url": "https://www.onbid.co.kr/", "image_url": None, "is_active": True,
        },
    ]
