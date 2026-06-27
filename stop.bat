@echo off
echo [Stop Service] Stopping OnBid-Backend and OnBid-Frontend...

:: 1. Try to stop using window title (interactive runs)
taskkill /FI "WindowTitle eq OnBid-Backend*" /T /F 2>nul
taskkill /FI "WindowTitle eq OnBid-Frontend*" /T /F 2>nul

:: 2. Try to stop using listening ports (background / service runs)
echo [Stop Service] Cleaning up processes on ports 8000, 8001, and 5173...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo [Port 8000] Stopping PID %%a...
    taskkill /F /PID %%a 2>nul
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do (
    echo [Port 8001] Stopping PID %%a...
    taskkill /F /PID %%a 2>nul
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    echo [Port 5173] Stopping PID %%a...
    taskkill /F /PID %%a 2>nul
)

echo Done.
