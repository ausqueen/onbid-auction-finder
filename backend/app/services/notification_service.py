"""
알림톡(카카오) 발송 서비스 — Solapi(솔라피) API 연동.

신규 가입 신청이 들어오면 관리자에게 알림톡을 보냅니다.
- 인증: HMAC-SHA256 (apiKey/apiSecret) — 별도 SDK 없이 httpx로 직접 호출.
- 알림톡 실패 시 SMS 대체발송(disableSms=False)로 자동 폴백.
- 필요한 설정값이 하나라도 비어 있으면 조용히 스킵(무동작)하므로,
  키를 .env 에 넣기 전까지는 운영에 영향이 없습니다.

준비물(운영자):
  1) 카카오 비즈니스 채널 개설 + Solapi 계정에 채널 연동(pfId 발급)
  2) 알림톡 템플릿 등록·심사 통과(templateId 발급)
  3) Solapi 발신번호(문자 대체발송용) 사전 등록
  4) .env 에 아래 값 설정 후 백엔드 재빌드·재기동
     SOLAPI_API_KEY, SOLAPI_API_SECRET, ALIMTALK_PF_ID,
     ALIMTALK_TEMPLATE_ID, ALIMTALK_SENDER, ADMIN_PHONE
"""
import hmac
import hashlib
import logging
import secrets
from datetime import datetime, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

SOLAPI_SEND_URL = "https://api.solapi.com/messages/v4/send"


def _auth_header(api_key: str, api_secret: str) -> str:
    """Solapi HMAC-SHA256 인증 헤더 생성."""
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    salt = secrets.token_hex(16)
    signature = hmac.new(
        api_secret.encode("utf-8"),
        (date + salt).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return (
        f"HMAC-SHA256 apiKey={api_key}, date={date}, "
        f"salt={salt}, signature={signature}"
    )


def notify_admin_new_signup(name: str, username: str, phone: str) -> None:
    """
    신규 가입 신청을 관리자에게 알림톡으로 통지.
    BackgroundTasks 로 호출되며, 실패해도 예외를 밖으로 던지지 않음(가입 흐름 보호).
    """
    s = get_settings()

    required = {
        "SOLAPI_API_KEY": s.solapi_api_key,
        "SOLAPI_API_SECRET": s.solapi_api_secret,
        "ALIMTALK_PF_ID": s.alimtalk_pf_id,
        "ALIMTALK_TEMPLATE_ID": s.alimtalk_template_id,
        "ALIMTALK_SENDER": s.alimtalk_sender,
        "ADMIN_PHONE": s.admin_phone,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        logger.info("알림톡 설정 미완료 — 발송 스킵 (누락: %s)", ", ".join(missing))
        return

    # 심사 통과한 템플릿의 치환 변수(#{...})와 정확히 일치해야 함.
    # 예시 템플릿:
    #   [원부동산] 신규 가입 신청
    #   · 이름: #{name}
    #   · 아이디: #{username}
    #   · 연락처: #{phone}
    #   관리자 승인 대기 중입니다.
    variables = {
        "#{name}": name,
        "#{username}": username,
        "#{phone}": phone,
    }
    # 알림톡 실패 시 SMS 대체발송에 쓰일 본문
    fallback_text = (
        f"[원부동산] 신규 가입 신청\n"
        f"이름: {name}\n아이디: {username}\n연락처: {phone}\n"
        f"관리자 승인 대기 중입니다."
    )

    payload = {
        "message": {
            "to": s.admin_phone.replace("-", ""),
            "from": s.alimtalk_sender.replace("-", ""),
            "text": fallback_text,
            "kakaoOptions": {
                "pfId": s.alimtalk_pf_id,
                "templateId": s.alimtalk_template_id,
                "variables": variables,
                "disableSms": False,  # 알림톡 실패 시 SMS 대체발송
            },
        }
    }

    try:
        headers = {
            "Authorization": _auth_header(s.solapi_api_key, s.solapi_api_secret),
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(SOLAPI_SEND_URL, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("알림톡 발송 실패 (%s): %s", resp.status_code, resp.text)
        else:
            logger.info("알림톡 발송 성공 — 신규 신청 %s(%s)", name, username)
    except Exception:  # 알림 실패가 가입을 막지 않도록 격리
        logger.exception("알림톡 발송 중 예외 발생 — 신규 신청 %s(%s)", name, username)
