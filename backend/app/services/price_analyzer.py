"""
가격 분석 엔진
Gap 분석, 수익률 계산, 취득세 추정
"""

from typing import Optional


def calc_gap(min_bid: int, market_price: int, tenant_deposit: int = 0) -> dict:
    """
    시세차익(Gap) 계산

    Args:
        min_bid: 최저입찰가(원)
        market_price: 추정 시세(원)
        tenant_deposit: 임차인 인수금액(원)

    Returns:
        gap_amount: 시세차익(원)
        gap_pct: 시세차익률(%)
    """
    if market_price <= 0:
        return {"gap_amount": 0, "gap_pct": 0.0}

    # 총 필요 자금 = 최저입찰가 + 인수보증금
    total_cost = min_bid + tenant_deposit
    gap_amount = market_price - total_cost
    gap_pct = round(gap_amount / market_price * 100, 2)
    return {"gap_amount": gap_amount, "gap_pct": gap_pct}


def estimate_acquisition_tax(price: int, property_type: str) -> int:
    """
    취득세 간이 추정

    세율 기준 (2024년):
    - 주택 6억 이하: 1%
    - 주택 6~9억: 1~3% 구간세율 (간략화: 2%)
    - 주택 9억 초과 or 다주택: 3%
    - 토지/상가/기타: 4%
    - 농지: 2.3% (농지취득세 특례)
    - 지방교육세 포함하여 약 0.1~0.4% 추가

    Args:
        price: 취득가액(원) - 낙찰가 기준
        property_type: 물건종류

    Returns:
        추정 취득세(원)
    """
    APARTMENT_TYPES = {"아파트", "빌라/연립", "단독/다가구", "오피스텔"}
    LAND_TYPES = {"토지", "임야"}
    FARM_TYPES = {"농지"}

    if property_type in APARTMENT_TYPES:
        if price <= 600_000_000:
            rate = 0.011  # 1% + 지방교육세 0.1%
        elif price <= 900_000_000:
            rate = 0.022  # 2% + 지방교육세 0.2%
        else:
            rate = 0.033  # 3% + 지방교육세 0.3%
    elif property_type in FARM_TYPES:
        rate = 0.023  # 농지 2.3%
    else:
        rate = 0.044  # 토지/상가/기타 4% + 지방교육세 0.4%

    return int(price * rate)


def calc_score(
    gap_pct: float,
    fail_count: int,
    has_risk: bool,
    appraisal_value: Optional[int] = None,
    market_price: Optional[int] = None,
    tenant_deposit: int = 0,
    has_unknown_risk: bool = False,
) -> float:
    """
    추천 점수 계산 (높을수록 좋음)

    산식:
    - base = gap_pct * 0.7 + fail_count_bonus * 0.3
    - 감정가 > 시세 과평가 페널티 적용
    - 위험 물건 감점: 인수금이 불명확한 위엄(또는 맹지 등)은 50% 감점, 인수금이 파악된 단순 대항력은 20%만 감점

    Args:
        gap_pct: 시세차익률(%)
        fail_count: 유찰횟수
        has_risk: 위험 키워드 포함 여부
        appraisal_value: 감정평가액(원) - 과평가 체크용
        market_price: 추정 시세(원)
        tenant_deposit: 파악된 인수 보증금 (원)
        has_unknown_risk: 파악 불가능한 고위험(맹지, 유치권, 미상 보증금 등) 여부

    Returns:
        점수 (0.0 ~ 100.0+)
    """
    # 유찰횟수 보너스 (최대 20점 캡)
    fail_bonus = min(fail_count * 5.0, 20.0)

    # 기본 점수
    base = gap_pct * 0.7 + fail_bonus * 0.3

    # 감정가 과평가 페널티 & 가짜 시세차익 방지 페널티
    if appraisal_value and market_price and market_price > 0:
        if appraisal_value > market_price * 1.1:
            base *= 0.8  # 과대평가 물건 페널티
        elif appraisal_value < market_price * 0.2:
            # 감정가가 시세의 20%도 안 될 경우: 지분/토지제외 등 불완전 매각이 확실하므로 Fake Gap으로 처리
            base *= 0.1
    
    # 2차 Fake Gap 필터: 최저입찰가가 감정가의 10% 미만인 경우 (단순 임대/대부 물건이거나 Kamco API 데이터 오류)
    # 예: 감정가는 2억인데 최저입찰가가 199만원인 기이한 물건
    # 단, 이 로직을 적용하려면 인자로 min_bid_price를 확인해야 하지만 인자가 없으므로,
    # gap_pct 가 90%를 초과할 정도로 비상식적일 때만 보수적으로 깎아냅니다.
    if gap_pct > 85.0:
        base *= 0.2  # 시세 대비 85% 이상 저렴한 물건은 상식적으로 불가능한 허위지분/데이터오류이므로 최상단에 뜨지 못하게 페널티


    # 위험 물건 감점
    if has_risk:
        if has_unknown_risk:
            base *= 0.5  # 폭탄 매물: 50% 삭감
        else:
            base *= 0.8  # 보증금이 이미 계산에 들어갔으므로, 명도 난이도에 대한 20% 페널티만 부여

    return round(max(base, 0.0), 2)


def estimate_market_price_from_appraisal(
    appraisal_value: int,
    fail_count: int,
    property_type: str,
) -> int:
    """
    실거래가 API 없을 때 감정평가액 기반 시세 추정

    전략:
    - 감정평가액은 보수적으로 평가되는 경향이 있음
    - 아파트: 감정가 * 1.05 ~ 1.15 (수요지에 따라)
    - 토지: 감정가 * 0.9 ~ 1.0 (토지는 비교적 정확)
    - 상가: 감정가 * 0.95 ~ 1.05

    여기서는 물건 유형별 보정 계수 적용
    """
    MULTIPLIERS = {
        "아파트": 1.10,
        "빌라/연립": 1.05,
        "단독/다가구": 1.05,
        "오피스텔": 1.03,
        "상가": 1.00,
        "토지": 0.95,
        "농지": 0.90,
        "임야": 0.85,
        "공장/창고": 0.95,
        "기타": 1.00,
    }
    multiplier = MULTIPLIERS.get(property_type, 1.00)
    return int(appraisal_value * multiplier)


def analyze_price(
    min_bid_price: int,
    appraisal_value: Optional[int],
    fail_count: int,
    property_type: str,
    market_price_from_api: Optional[int] = None,
    tenant_deposit: int = 0,
) -> dict:
    """
    종합 가격 분석

    Args:
        min_bid_price: 최저입찰가
        appraisal_value: 감정평가액
        fail_count: 유찰횟수
        property_type: 물건종류
        market_price_from_api: 국토부 API에서 가져온 실거래가 (없으면 None)
        tenant_deposit: 임차인 인수보증금 (옵션)

    Returns:
        market_price, gap_amount, gap_pct, acquisition_tax, score 포함 dict
    """
    # 시세 결정: API 값 우선, 없으면 감정가 기반 추정
    if market_price_from_api and market_price_from_api > 0:
        market_price = market_price_from_api
    elif appraisal_value and appraisal_value > 0:
        market_price = estimate_market_price_from_appraisal(
            appraisal_value, fail_count, property_type
        )
    else:
        market_price = min_bid_price  # 최저입찰가를 기준으로

    gap = calc_gap(min_bid_price, market_price, tenant_deposit)
    acquisition_tax = estimate_acquisition_tax(min_bid_price, property_type)

    return {
        "market_price": market_price,
        "gap_amount": gap["gap_amount"],
        "gap_pct": gap["gap_pct"],
        "acquisition_tax": acquisition_tax,
    }
