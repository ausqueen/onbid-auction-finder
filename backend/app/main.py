"""
온비드 공매 추천 서비스 - FastAPI 메인 앱
"""

import logging
import os
import sys
import asyncio
from dotenv import load_dotenv

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

load_dotenv()  # .env 값을 os.environ에 확실하게 적재

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .scheduler import start_scheduler, stop_scheduler
from .api.endpoints import properties, analysis, sync, test, bankruptcy, auth, admin, users


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("앱 시작 중...")
    init_db()
    
    # root 관리자 계정 자동 생성 (Seeding)
    from .database import SessionLocal
    from .models.user import User
    from .api.endpoints.auth import get_password_hash
    
    db = SessionLocal()
    try:
        root_user = db.query(User).filter(User.username == "root").first()
        if not root_user:
            logger.info("root 관리자 계정 생성 중...")
            new_root = User(
                username="root",
                hashed_password=get_password_hash("Realty!@34"),
                name="최고관리자",
                email="root@local.com",
                phone="010-0000-0000",
                is_approved=True,
                is_superuser=True
            )
            db.add(new_root)
            db.commit()
            logger.info("root 관리자 계정이 성공적으로 생성되었습니다.")
        else:
            logger.info("root 관리자 계정이 이미 존재합니다.")
    except Exception as e:
        logger.error(f"root 계정 생성 중 오류: {e}")
    finally:
        db.close()

    logger.info("DB 초기화 완료 (스케줄러는 윈도우 작업 스케줄러로 이관됨)")
    yield
    logger.info("앱 종료")


app = FastAPI(
    title=settings.app_name,
    description="온비드 공매 데이터 기반 부동산 물건 분석·추천 서비스",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .api.endpoints.auth import get_current_user

# 인증이 필요 없는 공용 API (로그인, 회원가입, ID/PW찾기)
app.include_router(auth.router, prefix="/api")

# 관리자/컨텐츠 보호 API (의존성 추가)
app.include_router(admin.router, prefix="/api")
app.include_router(users.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(properties.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(analysis.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(sync.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(test.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(bankruptcy.router, prefix="/api")


@app.get("/")
def root():
    return {"service": settings.app_name, "version": "1.0.0", "docs": "/docs"}


@app.get("/api/config/kakao")
def get_kakao_key():
    return {"kakao_js_api_key": settings.kakao_js_api_key}


@app.get("/api/config/naver")
def get_naver_key():
    return {"naver_client_id": settings.naver_client_id}


@app.get("/api/config/vworld")
def get_vworld_key():
    return {"vworld_api_key": settings.vworld_api_key or "28061B90-E735-3802-9ECD-0077C4F36B50"}


@app.get("/api/proxy/vworld/{path:path}")
async def proxy_vworld(path: str, request: Request):
    import httpx
    # Extract query parameters
    query_params = dict(request.query_params)
    
    # Inject Vworld key and domain if missing or blank
    if "key" not in query_params or not query_params["key"]:
        query_params["key"] = settings.vworld_api_key or "28061B90-E735-3802-9ECD-0077C4F36B50"
    if "domain" not in query_params:
        # Default to a safe placeholder or extract host from header
        host = request.headers.get("host", "localhost")
        query_params["domain"] = host.split(":")[0]
        
    vworld_url = f"https://api.vworld.kr/{path}"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(vworld_url, params=query_params)
            try:
                # Try returning as JSON
                return response.json()
            except Exception:
                # Fallback to plain text response (WMS image is binary, but Data API is JSON/XML)
                from fastapi.responses import Response
                return Response(content=response.content, media_type=response.headers.get("content-type"))
        except Exception as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/health")
def health():
    from .database import SessionLocal
    from .models.property import Property
    db = SessionLocal()
    try:
        props = db.query(Property).count()
    finally:
        db.close()
    return {"status": "ok", "api_key_len": len(settings.onbid_api_key), "prop_count": props}
