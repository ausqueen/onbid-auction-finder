@echo off
chcp 65001 > nul
echo ============================================================
echo  Let's Encrypt SSL 인증서 자동 발급 스크립트
echo  도메인: realty99.co.kr
echo ============================================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [오류] 관리자 권한으로 실행해주세요.
    echo 이 파일을 우클릭 - "관리자 권한으로 실행"
    pause
    exit /b 1
)

:: ── STEP 1: Windows 방화벽 포트 개방 ──────────────────────────
echo [1/5] Windows 방화벽 포트 80, 443 개방 중...
netsh advfirewall firewall delete rule name="Allow-HTTP-80" >nul 2>&1
netsh advfirewall firewall delete rule name="Allow-HTTPS-443" >nul 2>&1
netsh advfirewall firewall add rule name="Allow-HTTP-80" dir=in action=allow protocol=TCP localport=80
netsh advfirewall firewall add rule name="Allow-HTTPS-443" dir=in action=allow protocol=TCP localport=443
echo    완료

:: ── STEP 2: 인증서 저장 디렉토리 생성 ─────────────────────────
echo [2/5] 인증서 저장 디렉토리 생성 중...
if not exist "C:\win-acme\certs\realty99.co.kr" mkdir "C:\win-acme\certs\realty99.co.kr"
if not exist "C:\nginx\html\.well-known\acme-challenge" mkdir "C:\nginx\html\.well-known\acme-challenge"
echo    완료

:: ── STEP 3: nginx ACME 설정으로 시작 ──────────────────────────
echo [3/5] nginx 시작 (ACME challenge 용)...
taskkill /f /im nginx.exe >nul 2>&1
timeout /t 2 /nobreak >nul

copy /y "C:\nginx\conf\nginx_acme.conf" "C:\nginx\conf\nginx.conf" >nul
cd /d C:\nginx
start /b nginx.exe
timeout /t 3 /nobreak >nul

tasklist /fi "imagename eq nginx.exe" | findstr nginx.exe >nul
if %errorLevel% NEQ 0 (
    echo [오류] nginx 시작 실패!
    echo nginx 오류 로그 확인: C:\nginx\logs\error.log
    type C:\nginx\logs\error.log
    pause
    exit /b 1
)
echo    완료

:: DNS 전파 확인
echo.
echo [확인] realty99.co.kr 이 5.104.87.178 을 가리키는지 확인 중...
for /f "tokens=*" %%i in ('powershell -command "(Resolve-DnsName realty99.co.kr -Type A -Server 8.8.8.8 -ErrorAction SilentlyContinue).IPAddress"') do set RESOLVED_IP=%%i
echo    DNS 조회 결과: %RESOLVED_IP%
if not "%RESOLVED_IP%"=="5.104.87.178" (
    echo [경고] DNS가 아직 우리 서버를 가리키지 않습니다.
    echo    현재: %RESOLVED_IP%
    echo    필요: 5.104.87.178
    echo    DNS 전파가 완료될 때까지 기다린 후 다시 실행하세요.
    echo    (닷홈 DNS 변경 후 최대 1시간 소요)
    pause
    exit /b 1
)
echo    DNS 정상 확인!

:: ── STEP 4: win-acme으로 Let's Encrypt 인증서 발급 ─────────────
echo.
echo [4/5] Let's Encrypt 인증서 발급 중...
cd /d C:\win-acme

wacs.exe ^
    --source manual ^
    --host realty99.co.kr ^
    --validation filesystem ^
    --webroot "C:\nginx\html" ^
    --store pemfiles ^
    --pemfilespath "C:\win-acme\certs\realty99.co.kr" ^
    --accepttos ^
    --emailaddress "admin@realty99.co.kr" ^
    --notaskscheduler

if %errorLevel% NEQ 0 (
    echo.
    echo [오류] 인증서 발급 실패!
    echo 확인 사항:
    echo   1. realty99.co.kr 이 5.104.87.178 을 가리키는지
    echo   2. Azure NSG에서 포트 80이 허용됐는지
    echo   3. Windows 방화벽이 포트 80을 허용하는지
    pause
    exit /b 1
)

echo    인증서 발급 완료!
echo    위치: C:\win-acme\certs\realty99.co.kr\
dir "C:\win-acme\certs\realty99.co.kr\"

:: ── STEP 5: 최종 HTTPS nginx 설정으로 전환 ─────────────────────
echo.
echo [5/5] nginx HTTPS 설정으로 전환 중...
taskkill /f /im nginx.exe >nul 2>&1
timeout /t 2 /nobreak >nul

copy /y "C:\nginx\conf\nginx_final.conf" "C:\nginx\conf\nginx.conf" >nul
cd /d C:\nginx
start /b nginx.exe
timeout /t 3 /nobreak >nul

tasklist /fi "imagename eq nginx.exe" | findstr nginx.exe >nul
if %errorLevel% NEQ 0 (
    echo [오류] HTTPS nginx 시작 실패!
    type C:\nginx\logs\error.log
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  SSL 인증서 적용 완료!
echo  브라우저에서 확인: https://realty99.co.kr
echo ============================================================
echo.
pause
