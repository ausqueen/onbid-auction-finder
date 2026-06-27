"""
위험 분석 엔진
키워드 기반 위험 분류, 맹지/농취증 태깅
"""

import json
from typing import Optional

# 법적/재산 위험 키워드
RISK_KEYWORDS = [
    "유치권",
    "법정지상권",
    "지상권",
    "대항력",
    "대항력 있는 임차인",
    "지분매각",
    "지분",
    "가처분",
    "가압류",
    "압류",
    "임차권등기",
    "예고등기",
    "분묘기지권",
    "특수조건",
]

# 맹지 관련 키워드
BLIND_LAND_KEYWORDS = [
    "맹지",
    "도로 없음",
    "도로없음",
    "진입로 불분명",
    "진입로불분명",
    "접도 없음",
    "접도없음",
    "도로 미접함",
    "도로미접",
    "포위토지",
]

# 농지취득자격증명(농취증) 필요 지목
FARM_LAND_CATEGORIES = {
    "전",       # 밭
    "답",       # 논
    "과수원",   # 과수원
    "목장용지", # 목장
}

# 고위험 키워드 (즉시 위험 분류)
HIGH_RISK_KEYWORDS = [
    "유치권",
    "법정지상권",
    "대항력",
    "지분매각",
    "가처분",
]


def analyze_risk(
    description: Optional[str],
    land_category: Optional[str],
    property_type: Optional[str] = None,
) -> dict:
    """
    위험 분석

    Args:
        description: 물건 설명 / 공고문 내용
        land_category: 지목 (토지의 경우)
        property_type: 물건종류

    Returns:
        risk_keywords: 감지된 위험 키워드 목록
        risk_keywords_json: JSON 문자열
        is_blind_land: 맹지 여부
        needs_farm_cert: 농취증 필요 여부
        is_safe: 안전 물건 여부
        risk_level: "HIGH" / "MEDIUM" / "LOW"
    """
    text = (description or "").strip()
    lc = (land_category or "").strip()

    # 위험 키워드 감지
    found_risks = [kw for kw in RISK_KEYWORDS if kw in text]

    # 오탐 방지: 공공기관 특유의 안내 문구("대항력 여부 사전확인 요망")를 위험으로 탐지하지 않도록 필터링
    filtered_risks = []
    for kw in found_risks:
        if kw == "대항력":
            # 텍스트 내의 '대항력' 주변 문맥 파악
            # 대항력이라는 단어가 들어있지만, 그것이 "대항력 여부", "대항력유무", "대항력 등" 단순 안내일 뿐이라면 제외
            # 단, "대항력 있음", "대항력을 갖춘", "대항력있는" 등은 진짜 위험
            if text.count("대항력") == text.count("대항력 여부") + text.count("대항력여부") + text.count("대항력 유무") + text.count("대항력유무") + text.count("대항력 등"):
                continue # 안내 문구만 있다면 패스
        filtered_risks.append(kw)

    found_risks = filtered_risks
    high_risks = [kw for kw in HIGH_RISK_KEYWORDS if kw in filtered_risks]

    # 맹지 여부
    is_blind_land = any(kw in text for kw in BLIND_LAND_KEYWORDS)

    # 농취증 필요 여부: 지목이 농지 분류에 해당하거나 설명에 "농취증" 언급
    needs_farm_cert = (
        lc in FARM_LAND_CATEGORIES
        or "농취증" in text
        or "농지취득자격증명" in text
    )

    # 안전 여부
    is_safe = (
        len(found_risks) == 0
        and not is_blind_land
    )

    # 위험 등급
    if high_risks or is_blind_land:
        risk_level = "HIGH"
    elif found_risks or needs_farm_cert:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # 임차인 인수금(보증금) 추출기 (Regex) 방어적 숫자 추출 패턴
    import re
    tenant_deposit = 0
    if "대항력" in text or "보증금" in text or "전세" in text:
        # 1) 원/금 단위 거액 추출 (숫자와 콤마 조합, 최소한 백만 원 단위 이상이므로 7자리 숫자 이상)
        # 매치: "보증금 150,000,000원", "금165,000,000", "임차금 4,400,000"
        # 주의: 방 번호 "1, 201, 202" 등이 잡히지 않도록, 보증금/전세금/임차/권자/금 이라는 맥락 단어를 앞에 둠
        matches_won = re.findall(r'(?:보증금|전세금|임차금|권자|금)\s*([0-9]{1,4}(?:,[0-9]{3}){1,})', text)
        for m in matches_won:
            val_str = m.replace(',', '')
            if val_str.isdigit():
                val = int(val_str)
                if val > tenant_deposit and val >= 1000000:
                    tenant_deposit = val
        
        # 2) 만약 거액 원 단위를 못 찾았다면, "만" 단위 수치 탐색 (예: 5,000만원)
        if tenant_deposit == 0:
            matches_man = re.findall(r'([0-9,]+)\s*만\s*(?:원)?', text)
            for m in matches_man:
                val_str = m.replace(',', '')
                if val_str.isdigit():
                    val = int(val_str) * 10000
                    if val > tenant_deposit and val >= 1000000:
                        tenant_deposit = val

        # 3) "억" 단위 단일 숫자 탐색 (예: 전세 2억)
        if tenant_deposit == 0:
            matches_eok = re.findall(r'([0-9,]+)\s*억', text)
            for m in matches_eok:
                val_str = m.replace(',', '')
                if val_str.isdigit():
                    val = int(val_str) * 100000000
                    if val > tenant_deposit:
                        tenant_deposit = val

    return {
        "risk_keywords": found_risks,
        "risk_keywords_json": json.dumps(found_risks, ensure_ascii=False),
        "is_blind_land": is_blind_land,
        "needs_farm_cert": needs_farm_cert,
        "is_safe": is_safe,
        "risk_level": risk_level,
        "tenant_deposit": tenant_deposit,
    }
