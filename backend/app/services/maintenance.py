"""
온비드 물건 활성 상태 유지보수 (2026-07-12 신설)

상세 API로 is_active=True 후보를 검증해, 실제로 사라진(낙찰/취소/삭제) 물건만 is_active=False 로 정리한다.
공매는 다회 유찰로 수개월 지속되므로 updated_at 노후만으로는 종료가 아님(검증 결과 30일+ 미갱신 물건도 대부분 활성).
따라서 상세 API가 'not found'(resultCode≠00 또는 item 없음)일 때만 만료 처리한다 → 활성 물건 오판 0.

목록 API는 전체(5만+행)를 truncation 없이 못 가져오므로 "목록에 없음=종료" 판정은 불가.
그래서 절대 신호인 상세 API 존재 여부로만 판정한다.

호출량(쿼터) 방어: 오래된(updated_at) 순으로 max_checks 개만 검증, 429 감지 시 즉시 중단.
검증된 활성 물건은 updated_at 을 갱신해 stale 창에서 빼내 다음 주기까지 재검증에서 제외(진행성 보장).
"""

import time
import logging
import httpx
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from sqlalchemy.orm import Session

from ..models.property import Property
from ..config import get_settings
from .onbid_client import _parse_datetime

logger = logging.getLogger(__name__)
settings = get_settings()


def _detail_status(notice_no: str) -> dict:
    """상세 API 조회 → {gone, rate_limited, error, bid_end}."""
    url = f"{settings.onbid_base_url}/OnbidRlstDtlSrvc2/getRlstDtlInf2"
    out = {"gone": False, "rate_limited": False, "error": False, "bid_end": None}
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(url, params={
                "serviceKey": settings.onbid_api_key,
                "cltrMngNo": notice_no,
                "resultType": "xml",
            })
            if r.status_code == 429:
                out["rate_limited"] = True
                return out
            r.raise_for_status()
        root = ET.fromstring(r.text)
        rc = root.findtext(".//resultCode")
        item = root.find(".//item")
        if (rc not in (None, "00")) or item is None:
            out["gone"] = True
            return out
        # 실제(비-sentinel) 마감일 중 최댓값 → 있으면 미래 회차 존재
        ends = [_parse_datetime(e.text) for e in root.findall(".//cltrBidEndDt") if e.text]
        ends = [e for e in ends if e is not None]
        out["bid_end"] = max(ends) if ends else None
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 429:
            out["rate_limited"] = True
        else:
            out["error"] = True
    except Exception as e:
        logger.debug(f"상세 검증 오류 {notice_no}: {e}")
        out["error"] = True
    return out


def verify_stale_active(
    db: Session,
    stale_days: int = 21,
    max_checks: int = 300,
    delay: float = 0.25,
) -> dict:
    """오래 미갱신된 is_active 물건을 상세 API로 검증.

    - GONE(상세 없음)  → is_active=False (만료)
    - 존재            → bid_end_dt 갱신 + updated_at 갱신(재검증 유예)
    429 감지 시 즉시 중단. max_checks 로 1회 호출량 제한(쿼터 방어).
    """
    logger.info(f"활성상태 검증 시작 (stale_days={stale_days}, max_checks={max_checks})")
    cutoff = datetime.utcnow() - timedelta(days=stale_days)
    candidates = (
        db.query(Property)
        .filter(Property.is_active == True, Property.updated_at < cutoff)
        .order_by(Property.updated_at.asc())
        .limit(max_checks)
        .all()
    )

    checked = expired = still_active = errors = 0
    rate_limited = False
    for prop in candidates:
        st = _detail_status(prop.notice_no)
        if st["rate_limited"]:
            rate_limited = True
            logger.warning("상세 429 감지 — 활성상태 검증 중단(다음 실행에서 계속)")
            break
        if st["error"]:
            errors += 1
            time.sleep(delay)
            continue
        checked += 1
        if st["gone"]:
            prop.is_active = False
            expired += 1
            logger.info(f"만료 처리(상세 없음): {prop.notice_no} | {prop.address}")
        else:
            if st["bid_end"]:
                prop.bid_end_dt = st["bid_end"]
            prop.updated_at = datetime.utcnow()  # 검증 완료 → stale 창에서 제외
            still_active += 1
        db.commit()
        time.sleep(delay)

    result = {
        "candidates": len(candidates),
        "checked": checked,
        "expired": expired,
        "still_active": still_active,
        "errors": errors,
        "rate_limited": rate_limited,
    }
    logger.info(f"활성상태 검증 완료: {result}")
    return result
