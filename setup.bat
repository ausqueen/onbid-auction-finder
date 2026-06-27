@echo off
chcp 65001 > nul
echo ============================================================
echo  온비드 공매 추천 서비스 - 최초 설치 (Windows)
echo ============================================================

:: ── 1. Python 가상환경 ───────────────────────────────────────
echo [1/5] Python 가상환경 생성 중...
cd backend
python -m venv .venv
call .venv\Scripts\activate.bat

:: ── 2. Python 패키지 설치 ────────────────────────────────────
echo [2/5] Python 패키지 설치 중...
pip install --upgrade pip
pip install -r requirements.txt

:: ── 3. Playwright 브라우저 설치 ──────────────────────────────
echo [3/5] Playwright Chromium 설치 중...
playwright install chromium

:: ── 4. .env 파일 생성 ────────────────────────────────────────
echo [4/5] 환경변수 파일 설정...
if not exist .env (
    copy .env.example .env
    echo.
    echo  !! .env 파일이 생성되었습니다. 아래 항목을 반드시 입력하세요:
    echo     - ONBID_API_KEY  : 공공데이터포털 온비드 API 키
    echo     - MOLIT_API_KEY  : 공공데이터포털 국토부 API 키
    echo     - GEMINI_API_KEY : Google AI Studio API 키
    echo  !! backend\.env 파일을 열어 값을 입력한 후 start.bat 을 실행하세요.
) else (
    echo  .env 파일이 이미 존재합니다. 기존 설정을 유지합니다.
)

cd ..

:: ── 5. Node.js 패키지 설치 ───────────────────────────────────
echo [5/5] Node.js 패키지 설치 중...
cd frontend
npm install
cd ..

echo.
echo ============================================================
echo  설치 완료!
echo  다음 단계:
echo    1. backend\.env 파일에 API 키 입력
echo    2. start.bat 실행
echo ============================================================
pause
