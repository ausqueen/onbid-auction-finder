"""
데이터 동기화 오케스트레이터
온비드 수집 → 상세 조회 → 시세 조회 → 분석 → DB 저장
"""

import time
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.property import Property, MarketPrice, AnalysisResult
from ..services.onbid_client import fetch_all_properties, fetch_property_detail
from ..services.molit_client import get_market_price_estimate
from ..services.price_analyzer import analyze_price, calc_score
from ..services.risk_analyzer import analyze_risk
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 마지막 동기화 시각 (메모리 캐시)
_last_synced_at: datetime | None = None

# 동기화 진행 상태 (메모리 캐시)
_sync_progress: dict = {
    "total_fetched": 0,   # 온비드 API에서 수집된 총 물건 수
    "processed": 0,       # 처리(분석+저장) 완료된 물건 수
    "created": 0,
    "updated": 0,
    "errors": 0,
    "current_address": "",  # 현재 처리 중인 물건 주소
}


def get_last_synced_at() -> datetime | None:
    return _last_synced_at


def get_sync_progress() -> dict:
    return dict(_sync_progress)


def sync_properties(db: Session) -> dict:
    """
    전체 동기화 실행

    1. 온비드 API에서 공매 물건 목록 수집
    1.5. 각 물건 상세 조회로 설명/지목/이미지 보완
    2. DB upsert (notice_no 기준)
    3. 국토부 실거래가 조회
    4. 가격/위험 분석
    5. DB 저장 (begin_nested SAVEPOINT: 물건 단위 롤백)

    Returns:
        동기화 결과 요약 dict
    """
    global _last_synced_at, _sync_progress

    logger.info("동기화 시작")
    start_time = datetime.utcnow()

    # 진행 상태 초기화
    _sync_progress = {
        "total_fetched": 0,
        "processed": 0,
        "created": 0,
        "updated": 0,
        "errors": 0,
        "current_address": "온비드 API에서 물건 목록 수집 중...",
    }

    # 1. 온비드 물건 수집
    raw_properties = fetch_all_properties(max_pages=settings.max_pages)
    logger.info(f"온비드 수집: {len(raw_properties)}건")
    _sync_progress["total_fetched"] = len(raw_properties)
    _sync_progress["current_address"] = f"{len(raw_properties)}건 수집 완료, 분석 시작 중..."

    created = 0
    updated = 0
    analyzed = 0
    errors = 0

    for idx, raw in enumerate(raw_properties):
        _sync_progress["current_address"] = raw.get("address", "")
        try:
            # 1.5 상세 정보 조회 (V2 차세대 대응 - 설명, 지목, 이미지 보완)
            detail = fetch_property_detail(raw["notice_no"])
            if detail["description"]:
                base_desc = raw.get("description") or ""
                raw["description"] = f"{base_desc}\n\n{detail['description']}".strip()
            if detail["image_url"]:
                raw["image_url"] = detail["image_url"]
            if detail["land_category"]:
                raw["land_category"] = detail["land_category"]
            time.sleep(0.3)  # 상세 조회 API 부하 방지 딜레이

            with db.begin_nested():  # SAVEPOINT: 실패 시 이 물건만 롤백, 다른 물건에 영향 없음
                # 2. DB upsert (notice_no 기준)
                prop = db.query(Property).filter(
                    Property.notice_no == raw["notice_no"]
                ).first()

                if prop is None:
                    prop = Property(**raw)
                    db.add(prop)
                    db.flush()  # ID 할당
                    created += 1
                else:
                    for key, value in raw.items():
                        setattr(prop, key, value)
                    prop.updated_at = datetime.utcnow()
                    updated += 1

                db.flush()

                # 3. 시세 조회 (국토부 API)
                market_price_api = None
                if prop.sido and prop.area_m2:
                    market_price_api = get_market_price_estimate(
                        sido=prop.sido,
                        property_type=prop.property_type,
                        area_m2=prop.area_m2,
                        sigungu=prop.sigungu,
                    )
                    if market_price_api:
                        # 기존 시세 삭제 후 재저장 (동기화 중복 방지)
                        db.query(MarketPrice).filter(
                            MarketPrice.property_id == prop.id
                        ).delete()
                        mp = MarketPrice(
                            property_id=prop.id,
                            source="molit",
                            price=market_price_api,
                            price_per_m2=int(market_price_api / prop.area_m2) if prop.area_m2 else None,
                            deal_date=datetime.utcnow().strftime("%Y%m"),
                        )
                        db.add(mp)

                # 5. 위험 분석 (먼저 해서 인수금액을 뽑아냄)
                risk_result = analyze_risk(
                    description=prop.description,
                    land_category=prop.land_category,
                    property_type=prop.property_type,
                )

                # 4. 가격 분석 (인수금액 반영)
                price_result = analyze_price(
                    min_bid_price=prop.min_bid_price,
                    appraisal_value=prop.appraisal_value,
                    fail_count=prop.fail_count,
                    property_type=prop.property_type,
                    market_price_from_api=market_price_api,
                    tenant_deposit=risk_result.get("tenant_deposit", 0),
                )

                # ========= 온비드 실시간 크롤링은 별도 스케줄로 분리 (sync 중 asyncio 충돌 방지) =========
                # 보증금 미파악 물건은 일단 is_unknown_risk=True로 저장, 추후 개별 분석
                # ================================================================================
                tenant_deposit_val = risk_result.get("tenant_deposit", 0)
                is_unknown_risk = not risk_result["is_safe"] and (
                    tenant_deposit_val == 0 or risk_result["is_blind_land"] 
                    or any(k in risk_result["risk_keywords_json"] for k in ["분묘", "지분", "가처분"])
                )

                score = calc_score(
                    gap_pct=price_result["gap_pct"],
                    fail_count=prop.fail_count,
                    has_risk=not risk_result["is_safe"],
                    appraisal_value=prop.appraisal_value,
                    market_price=price_result["market_price"],
                    tenant_deposit=tenant_deposit_val,
                    has_unknown_risk=is_unknown_risk,
                )

                # 7. 분석 결과 저장 (upsert)
                analysis = db.query(AnalysisResult).filter(
                    AnalysisResult.property_id == prop.id
                ).first()

                if analysis is None:
                    analysis = AnalysisResult(property_id=prop.id)
                    db.add(analysis)

                analysis.market_price = price_result["market_price"]
                analysis.gap_amount = price_result["gap_amount"]
                analysis.gap_pct = price_result["gap_pct"]
                analysis.acquisition_tax = price_result["acquisition_tax"]
                analysis.risk_keywords = risk_result["risk_keywords_json"]
                analysis.is_blind_land = risk_result["is_blind_land"]
                analysis.needs_farm_cert = risk_result["needs_farm_cert"]
                analysis.is_safe = risk_result["is_safe"]
                analysis.tenant_deposit = tenant_deposit_val
                analysis.score = score
                analysis.analyzed_at = datetime.utcnow()

                analyzed += 1

            # ★ 물건마다 즉시 commit — 읽기 응답성 보장, 중간 재시작해도 이미 저장된 데이터 안전
            db.commit()

            # 진행 상태 업데이트
            _sync_progress["processed"] = idx + 1
            _sync_progress["created"] = created
            _sync_progress["updated"] = updated
            _sync_progress["errors"] = errors

            if (idx + 1) % 10 == 0:
                logger.info(f"동기화 진행: {idx + 1}/{len(raw_properties)}건 처리 완료")

        except Exception as e:
            logger.error(f"물건 처리 오류 {raw.get('notice_no', '?')}: {e}")
            errors += 1
            _sync_progress["errors"] = errors
            continue

    db.commit()
    _last_synced_at = datetime.utcnow()

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    result = {
        "total": len(raw_properties),
        "created": created,
        "updated": updated,
        "analyzed": analyzed,
        "errors": errors,
        "elapsed_sec": round(elapsed, 2),
        "synced_at": _last_synced_at.isoformat(),
    }
    logger.info(f"동기화 완료: {result}")
    return result
