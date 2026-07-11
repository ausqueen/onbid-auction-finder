from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 온비드 OpenAPI
    onbid_api_key: str = ""
    onbid_base_url: str = "https://apis.data.go.kr/B010003"

    # 국토부 실거래가 API
    molit_api_key: str = ""
    molit_base_url: str = "https://apis.data.go.kr/1613000"

    # Gemini 파산 공고 분석 API
    gemini_api_key: str = ""

    # 카카오 JavaScript API
    kakao_js_api_key: str = ""

    # 네이버 Cloud Maps API
    naver_client_id: str = ""
    naver_client_secret: str = ""

    # 브이월드 API Key (소스 하드코딩 제거 — .env VWORLD_API_KEY 로 주입. ⚠️ 기존 노출키는 재발급 필요)
    vworld_api_key: str = ""

    # 앱 설정
    app_name: str = "온비드 공매 추천 서비스"
    debug: bool = False
    db_url: str = "sqlite:///./onbid.db"

    # 스케줄러
    sync_hour: int = 9       # 매일 오전 09:00 동기화
    sync_minute: int = 0
    # 온비드 일일 동기화 on/off 플래그 (2026-06-29 비활성화: data.go.kr 상세 API 429 쿼터 초과 이슈)
    # 재개하려면 .env 에 ONBID_SYNC_ENABLED=true 설정 후 백엔드 재빌드·재기동
    onbid_sync_enabled: bool = False

    # 분석 파라미터
    min_gap_pct: float = 10.0     # 최소 Gap% (시세 대비 할인율)
    top_n: int = 20               # TOP 추천 물건 수
    max_pages: int = 10           # 온비드 API 최대 페이지 수

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # JWT 인증 — 기본값 없음(필수). .env JWT_SECRET_KEY 미설정 시 기동 실패(예측가능 키 폴백 차단).
    jwt_secret_key: str
    access_token_expire_minutes: int = 1440
    playwright_browsers_path: str = ""

    # root 관리자 시딩 비밀번호 (.env ROOT_INIT_PASSWORD). 미설정 시 root 자동생성 스킵.
    root_init_password: str = ""

    # 알림톡(Solapi) — 신규 가입 관리자 통지용. 하나라도 비면 notification_service 가 조용히 스킵.
    solapi_api_key: str = ""
    solapi_api_secret: str = ""
    alimtalk_pf_id: str = ""
    alimtalk_template_id: str = ""
    alimtalk_sender: str = ""
    admin_phone: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
