"""
데이터 동기화 오케스트레이터
온비드 수집 → (증분) 상세 조회 → 시세 조회 → 분석 → DB 저장

2026-07-12 증분화: 매 실행 전건 상세 조회(→data.go.kr 429 쿼터 초과)를 제거.
  - 물건을 먼저 DB에서 조회해 신규/회차변동/상세결측일 때만 상세(getRlstDtlInf2) 호출
  - 변경 없는 물건은 시세(molit)·분석 전체 스킵
  - 상세 호출 일일 상한 + 429 백오프(감지 시 이번 실행 상세 중단, 목록 데이터로 계속)
  - 시세는 실행 내 캐시로 동일 지역·면적 중복 조회 제거
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
    "skipped": 0,         # 변경 없어 상세·분석을 건너뛴 물건 수
    "detail_calls": 0,    # 이번 실행에서 실제 상세 API를 호출한 횟수
    "errors": 0,
    "current_address": "",  # 현재 처리 중인 물건 주소
}


def get_last_synced_at() -> datetime | None:
    return _last_synced_at


def get_sync_progress() -> dict:
    return dict(_sync_progress)


def _needs_detail(prop: Property | None, raw: dict) -> bool:
    """상세(getRlstDtlInf2) 조회가 필요한지 판단.

    상세는 설명/지목/이미지 보완용이며 공고당 사실상 1회면 충분(회차가 바뀌어도 설명은 그대로).
    따라서 신규이거나 설명이 결측일 때만 True → 상세 API 호출을 최소화해 쿼터를 아낀다.
    """
    if prop is None:
        return True
    if not (prop.description or "").strip():
        return True
    return False


def _needs_process(prop: Property | None, raw: dict) -> bool:
    """upsert·시세·분석을 다시 수행할지 판단.

    신규, 분석 결과 없음, 설명 결측, 또는 가격/회차 변동(=새 입찰)일 때만 True.
    그 외 변경 없는 물건은 전부 스킵해 시세(molit) 호출과 연산을 아낀다.
    """
    if prop is None or prop.analysis is None:
        return True
    if not (prop.description or "").strip():
        return True
    if (prop.min_bid_price or 0) != (raw.get("min_bid_price") or 0):
        return True
    if (prop.fail_count or 0) != (raw.get("fail_count") or 0):
        return True
    return False


def sync_properties(db: Session) -> dict:
    """
    증분 동기화 실행

    1. 온비드 API에서 공매 물건 목록 수집
    2. 각 물건을 DB 조회 → 신규/회차변동/상세결측일 때만 상세 조회로 보완
    3. DB upsert (notice_no 기준)
    4. 국토부 실거래가 조회(실행 내 캐시) + 가격/위험 분석
    5. DB 저장 (begin_nested SAVEPOINT: 물건 단위 롤백)
    변경 없는 물건은 상세·시세·분석을 모두 건너뛴다.

    Returns:
        동기화 결과 요약 dict
    """
    global _last_synced_at, _sync_progress

    logger.info("동기화 시작(증분)")
    start_time = datetime.utcnow()

    # 진행 상태 초기화
    _sync_progress = {
        "total_fetched": 0,
        "processed": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "detail_calls": 0,
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
    skipped = 0
    analyzed = 0
    errors = 0

    # 상세 조회 쿼터 방어 상태
    detail_calls = 0                 # 이번 실행 상세 호출 수
    detail_stop = False              # 429 감지 또는 상한 도달 시 이후 상세 조회 중단
    detail_budget_skipped = 0        # 상한/429로 상세를 건너뛴 신규·변동 물건 수

    # 시세(molit) 실행 내 캐시 — 동일 (시도, 시군구, 토지여부, 면적버킷) 중복 조회 제거
    market_cache: dict = {}

    def _cached_market_price(sido, property_type, area_m2, sigungu):
        key = (
            sido,
            sigungu,
            property_type in ("토지", "농지", "임야"),
            round((area_m2 or 0) / 5) * 5,
        )
        if key in market_cache:
            return market_cache[key]
        val = get_market_price_estimate(
            sido=sido,
            property_type=property_type,
            area_m2=area_m2,
            sigungu=sigungu,
        )
        market_cache[key] = val
        return val

    for idx, raw in enumerate(raw_properties):
        _sync_progress["current_address"] = raw.get("address", "")
        try:
            # 기존 물건 먼저 조회 (증분 판단의 기준)
            prop = db.query(Property).filter(
                Property.notice_no == raw["notice_no"]
            ).first()

            need_detail = _needs_detail(prop, raw)

            # 변경 없음(분석 존재 + 가격/회차 동일 + 설명 있음) → 상세·시세·분석 모두 스킵
            if not _needs_process(prop, raw):
                skipped += 1
                _sync_progress["processed"] = idx + 1
                _sync_progress["skipped"] = skipped
                continue

            # 상세(설명/지목/이미지)는 신규·결측일 때만 조회 (예산·429 범위 내에서만)
            if need_detail and not detail_stop:
                if detail_calls >= settings.onbid_detail_daily_limit:
                    detail_stop = True
                    detail_budget_skipped += 1
                    logger.warning(
                        f"온비드 상세 호출 상한({settings.onbid_detail_daily_limit}) 도달 "
                        f"— 이번 실행 상세 조회 중단, 목록 데이터로 계속"
                    )
                else:
                    detail = fetch_property_detail(raw["notice_no"])
                    detail_calls += 1
                    _sync_progress["detail_calls"] = detail_calls
                    if detail.get("_rate_limited"):
                        detail_stop = True
                        logger.warning(
                            "온비드 상세 429(쿼터 초과) 감지 — 이번 실행 상세 조회 중단, "
                            "목록 데이터로 계속(나머지는 다음 실행에서 픽업)"
                        )
                    else:
                        if detail["description"]:
                            base_desc = raw.get("description") or ""
                            raw["description"] = f"{base_desc}\n\n{detail['description']}".strip()
                        if detail["image_url"]:
                            raw["image_url"] = detail["image_url"]
                        if detail["land_category"]:
                            raw["land_category"] = detail["land_category"]
                        time.sleep(settings.onbid_detail_delay)  # 상세 조회 API 부하 방지 딜레이
            elif need_detail and detail_stop:
                detail_budget_skipped += 1

            with db.begin_nested():  # SAVEPOINT: 실패 시 이 물건만 롤백, 다른 물건에 영향 없음
                # 2. DB upsert (notice_no 기준)
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

                # 3. 시세 조회 (국토부 API, 실행 내 캐시)
                market_price_api = None
                if prop.sido and prop.area_m2:
                    market_price_api = _cached_market_price(
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
            _sync_progress["skipped"] = skipped
            _sync_progress["errors"] = errors

            if (idx + 1) % 50 == 0:
                logger.info(
                    f"동기화 진행: {idx + 1}/{len(raw_properties)}건 "
                    f"(신규 {created}, 갱신 {updated}, 스킵 {skipped}, 상세호출 {detail_calls})"
                )

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
        "skipped": skipped,
        "analyzed": analyzed,
        "detail_calls": detail_calls,
        "detail_budget_skipped": detail_budget_skipped,
        "detail_stopped": detail_stop,
        "errors": errors,
        "elapsed_sec": round(elapsed, 2),
        "synced_at": _last_synced_at.isoformat(),
    }
    logger.info(f"동기화 완료: {result}")
    return result
