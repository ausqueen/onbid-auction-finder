@echo off
set "PLAYWRIGHT_BROWSERS_PATH=C:\Users\admin\AppData\Local\ms-playwright"
cd /d "%~dp0"

:: Ensure log files and DB files exist and have Modify permission for Users group (SID: S-1-5-32-545)
for %%F in (
    "backend\server_backend.log"
    "frontend\server_frontend.log"
    "backend\sync_task.log"
    "backend\debug_log.txt"
    "backend\analyze_log.txt"
    "backend\backfill_meta.log"
    "backend\scourt_log.txt"
    "backend\onbid.db"
    "backend\onbid.db-wal"
    "backend\onbid.db-shm"
) do (
    if not exist "%%~F" (
        type nul > "%%~F"
    )
    icacls "%%~F" /grant *S-1-5-32-545:M >nul 2>&1
)

:: Ensure tmp_downloads exists and has Modify permission
if not exist "backend\tmp_downloads" (
    mkdir "backend\tmp_downloads"
)
icacls "backend\tmp_downloads" /grant *S-1-5-32-545:(OI)(CI)M >nul 2>&1

:: --- Start Backend ---
echo [%date% %time%] Starting FastAPI Backend... >> backend\server_backend.log
cd /d "%~dp0backend"
start /b "" cmd /c ".venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8001" >> server_backend.log 2>&1

:: Wait for backend to initialize
timeout /t 3 /nobreak > nul

:: --- Start Frontend ---
echo [%date% %time%] Starting Frontend Vite... >> "%~dp0frontend\server_frontend.log"
cd /d "%~dp0frontend"
set VITE_HTTPS=false
set VITE_PORT=5173
start /b "" cmd /c "npm run dev" >> server_frontend.log 2>&1

:: --- Start Nginx ---
echo [%date% %time%] Starting Nginx... >> "%~dp0backend\server_backend.log"
taskkill /f /im nginx.exe >nul 2>&1
timeout /t 2 /nobreak >nul
cd /d C:\nginx
start /b nginx.exe

