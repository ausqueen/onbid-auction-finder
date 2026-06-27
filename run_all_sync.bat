@echo off
set "PLAYWRIGHT_BROWSERS_PATH=C:\Users\admin\AppData\Local\ms-playwright"

cd /d "C:\antigravity\onbid-auction-finder\backend"
call .venv\Scripts\activate.bat

:: Ensure log files and DB files exist and have Modify permission for Users group (SID: S-1-5-32-545)
for %%F in (
    "sync_task.log"
    "debug_log.txt"
    "analyze_log.txt"
    "backfill_meta.log"
    "scourt_log.txt"
    "onbid.db"
    "onbid.db-wal"
    "onbid.db-shm"
) do (
    if not exist "%%~F" (
        type nul > "%%~F"
    )
    icacls "%%~F" /grant *S-1-5-32-545:M >nul 2>&1
)

:: Ensure tmp_downloads exists and has Modify permission
if not exist "tmp_downloads" (
    mkdir "tmp_downloads"
)
icacls "tmp_downloads" /grant *S-1-5-32-545:(OI)(CI)M >nul 2>&1

echo ============================================================ >> sync_task.log
echo [%date% %time%] Daily Sync Task Started >> sync_task.log
echo ============================================================ >> sync_task.log

echo [%date% %time%] [1/2] Scourt Scraper (Phase 1)... >> sync_task.log
python debug.py >> sync_task.log 2>&1

echo [%date% %time%] [1/2 done] Waiting 10s before Phase 2... >> sync_task.log
timeout /t 10 /nobreak > nul

echo [%date% %time%] [2/2] AI Analyzer (Phase 2)... >> sync_task.log
python analyze_worker.py >> sync_task.log 2>&1

echo [%date% %time%] Sync Task Completed successfully. >> sync_task.log
echo. >> sync_task.log
