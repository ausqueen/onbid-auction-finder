"""
테스트 API 엔드포인트
온비드 API / 국토부 API 연결 상태 및 데이터 확인용
"""
import httpx
import logging
from fastapi import APIRouter
from xml.etree import ElementTree as ET
from ...config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test", tags=["test"])
settings = get_settings()


@router.get("/config")
def test_config():
    """환경변수 설정 확인 (API 키는 마스킹)"""
    onbid_key = settings.onbid_api_key
    molit_key = settings.molit_api_key
    return {
        "onbid_api_key": f"{onbid_key[:8]}...{onbid_key[-4:]}" if onbid_key else "❌ 미설정",
        "molit_api_key": f"{molit_key[:8]}...{molit_key[-4:]}" if molit_key else "❌ 미설정",
        "db_url": settings.db_url,
        "sync_schedule": f"매일 {settings.sync_hour:02d}:{settings.sync_minute:02d}",
        "top_n": settings.top_n,
        "min_gap_pct": settings.min_gap_pct,
    }


@router.get("/onbid")
def test_onbid():
    """온비드 API 실제 호출 테스트
    NOTE: getRlstDtlInf2는 상세 조회 전용 서비스. cltrMngNo 미전달 시 오류 응답 정상.
    """
    url = f"{settings.onbid_base_url}/getRlstDtlInf2"
    params = {
        "serviceKey": settings.onbid_api_key,
        "numOfRows": 5,
        "pageNo": 1,
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)

        # 응답 미리보기 (처음 500자)
        raw_preview = resp.text[:500]

        try:
            root = ET.fromstring(resp.text)
            result_code = (
                root.findtext(".//resultCode")
                or root.findtext(".//errCode")
                or "?"
            )
            result_msg = (
                root.findtext(".//resultMsg")
                or root.findtext(".//errMsg")
                or ""
            )
            items = root.findall(".//item")
            return {
                "status": "✅ 연결 성공" if resp.status_code == 200 else f"⚠️ HTTP {resp.status_code}",
                "http_status": resp.status_code,
                "result_code": result_code,
                "result_msg": result_msg,
                "item_count": len(items),
                "raw_preview": raw_preview,
            }
        except ET.ParseError:
            return {
                "status": f"⚠️ XML 파싱 실패 (HTTP {resp.status_code})",
                "http_status": resp.status_code,
                "raw_preview": raw_preview,
            }

    except httpx.TimeoutException:
        return {"status": "❌ 타임아웃 (15초)", "error": "timeout"}
    except Exception as e:
        return {"status": "❌ 연결 실패", "error": str(e)}


@router.get("/molit")
def test_molit():
    """국토부 실거래가 API 실제 호출 테스트 (서울 아파트 최근 1개월)"""
    from datetime import date, timedelta
    today = date.today()
    prev_month = today.replace(day=1) - timedelta(days=1)
    deal_ym = prev_month.strftime("%Y%m")

    url = f"{settings.molit_base_url}/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
    params = {
        "serviceKey": settings.molit_api_key,
        "LAWD_CD": "11000",   # 서울
        "DEAL_YMD": deal_ym,
        "numOfRows": 5,
        "pageNo": 1,
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)

        raw_preview = resp.text[:500]

        try:
            root = ET.fromstring(resp.text)
            result_code = root.findtext(".//resultCode") or "?"
            result_msg = root.findtext(".//resultMsg") or ""
            items = root.findall(".//item")

            sample = []
            for item in items[:3]:
                def g(tag):
                    el = item.find(tag)
                    return el.text.strip() if el is not None and el.text else ""
                sample.append({
                    "아파트명": g("aptNm"),
                    "거래금액": g("dealAmount") + "만원",
                    "전용면적": g("excluUseAr") + "㎡",
                    "법정동": g("umdNm"),
                    "거래년월": f"{g('dealYear')}-{g('dealMonth')}",
                })

            return {
                "status": "✅ 연결 성공" if resp.status_code == 200 else f"⚠️ HTTP {resp.status_code}",
                "http_status": resp.status_code,
                "result_code": result_code,
                "result_msg": result_msg,
                "query_ym": deal_ym,
                "item_count": len(items),
                "sample_data": sample,
                "raw_preview": raw_preview,
            }
        except ET.ParseError:
            return {
                "status": f"⚠️ XML 파싱 실패 (HTTP {resp.status_code})",
                "http_status": resp.status_code,
                "raw_preview": raw_preview,
            }

    except httpx.TimeoutException:
        return {"status": "❌ 타임아웃 (15초)", "error": "timeout"}
    except Exception as e:
        return {"status": "❌ 연결 실패", "error": str(e)}


@router.get("/mock-sync")
def test_mock_sync_and_analyze():
    """목업 데이터로 동기화+분석 전체 파이프라인 테스트"""
    from ...services.onbid_client import _get_mock_properties
    from ...services.price_analyzer import analyze_price, calc_score
    from ...services.risk_analyzer import analyze_risk

    results = []
    for raw in _get_mock_properties():
        price = analyze_price(
            min_bid_price=raw["min_bid_price"],
            appraisal_value=raw["appraisal_value"],
            fail_count=raw["fail_count"],
            property_type=raw["property_type"],
        )
        risk = analyze_risk(
            description=raw["description"],
            land_category=raw["land_category"],
            property_type=raw["property_type"],
        )
        score = calc_score(
            gap_pct=price["gap_pct"],
            fail_count=raw["fail_count"],
            has_risk=not risk["is_safe"],
            appraisal_value=raw["appraisal_value"],
            market_price=price["market_price"],
        )
        results.append({
            "address": raw["address"],
            "property_type": raw["property_type"],
            "min_bid_price_억": round(raw["min_bid_price"] / 1e8, 2),
            "market_price_억": round(price["market_price"] / 1e8, 2),
            "gap_pct": f"{price['gap_pct']}%",
            "acquisition_tax_만": round(price["acquisition_tax"] / 1e4),
            "risk_keywords": risk["risk_keywords"],
            "is_safe": risk["is_safe"],
            "needs_farm_cert": risk["needs_farm_cert"],
            "score": score,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"total": len(results), "items": results}


@router.get("/full-pipeline")
def test_full_pipeline():
    """실제 DB 동기화 (온비드 API 키 있으면 실제 데이터, 없으면 목업) 후 TOP 5 반환"""
    from ...database import SessionLocal
    from ...services.sync_service import sync_properties
    from ...models.property import Property, AnalysisResult
    from sqlalchemy.orm import joinedload

    db = SessionLocal()
    try:
        sync_result = sync_properties(db)
        top = (
            db.query(Property)
            .options(joinedload(Property.analysis))
            .join(AnalysisResult, Property.id == AnalysisResult.property_id)
            .filter(Property.is_active == True)
            .order_by(AnalysisResult.score.desc())
            .limit(5)
            .all()
        )
        items = []
        for p in top:
            a = p.analysis
            items.append({
                "address": p.address,
                "property_type": p.property_type,
                "min_bid_price_억": round(p.min_bid_price / 1e8, 2),
                "gap_pct": f"{a.gap_pct}%" if a else "-",
                "score": a.score if a else 0,
                "is_safe": a.is_safe if a else True,
                "risk_keywords": a.risk_keywords if a else "[]",
            })
        return {"sync": sync_result, "top5": items}
    finally:
        db.close()
