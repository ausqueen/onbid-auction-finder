@echo off
chcp 65001 > nul
echo ============================================================
echo  온비드 공매 추천 서비스 시작
echo ============================================================

:: ── 백엔드 시작 (uvicorn) ────────────────────────────────────
echo [백엔드] FastAPI 서버 시작 중... (http://localhost:8001)
start "OnBid-Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"

:: 백엔드 초기화 대기
timeout /t 3 /nobreak > /dev/null

:: ── 프론트엔드 시작 (Vite) ───────────────────────────────────
echo [프론트엔드] Vite 개발 서버 시작 중... (https://localhost:5173)
start "OnBid-Frontend" cmd /k "cd /d %~dp0frontend && set VITE_HTTPS=true && set VITE_PORT=5173 && npm run dev"

echo.
echo ============================================================
echo  서비스가 시작되었습니다.
echo    - 프론트엔드: http://localhost:5173
echo    - 백엔드 API: http://localhost:8001
echo    - API 문서:   http://localhost:8001/docs
echo ============================================================
echo  종료하려면 stop.bat 을 실행하거나 창을 닫으세요.
