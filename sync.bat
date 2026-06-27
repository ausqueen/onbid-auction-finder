@echo off
chcp 65001 > nul
echo ============================================================
echo  Antigravity(GitHub) 최신 소스 동기화
echo ============================================================

:: ── 현재 변경사항 확인 ───────────────────────────────────────
git status --short
echo.

:: ── GitHub에서 최신 코드 pull ────────────────────────────────
echo [1/3] GitHub main 브랜치에서 최신 코드를 가져옵니다...
git pull origin main
if %errorlevel% neq 0 (
    echo  !! git pull 실패. 네트워크 연결을 확인하세요.
    pause
    exit /b 1
)

:: ── Python 패키지 업데이트 ───────────────────────────────────
echo [2/3] Python 패키지 업데이트...
cd backend
call .venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
cd ..

:: ── Node.js 패키지 업데이트 ──────────────────────────────────
echo [3/3] Node.js 패키지 업데이트...
cd frontend
npm install --silent
cd ..

echo.
echo ============================================================
echo  동기화 완료! 변경사항을 반영하려면 서비스를 재시작하세요.
echo    stop.bat  →  start.bat
echo ============================================================

set /p restart="지금 바로 재시작할까요? (Y/N): "
if /i "%restart%"=="Y" (
    call stop.bat
    timeout /t 2 /nobreak > /dev/null
    call start.bat
)
