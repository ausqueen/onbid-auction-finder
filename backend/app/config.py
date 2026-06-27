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

    # 앱 설정
    app_name: str = "온비드 공매 추천 서비스"
    debug: bool = False
    db_url: str = "sqlite:///./onbid.db"

    # 스케줄러
    sync_hour: int = 9       # 매일 오전 09:00 동기화
    sync_minute: int = 0

    # 분석 파라미터
    min_gap_pct: float = 10.0     # 최소 Gap% (시세 대비 할인율)
    top_n: int = 20               # TOP 추천 물건 수
    max_pages: int = 10           # 온비드 API 최대 페이지 수

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # JWT 인증
    jwt_secret_key: str = "secret-key-for-jwt-token-hashing"
    access_token_expire_minutes: int = 1440
    playwright_browsers_path: str = ""

    # 브이월드 API
    vworld_api_key: str = "28061B90-E735-3802-9ECD-0077C4F36B50"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
