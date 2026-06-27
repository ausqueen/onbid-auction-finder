@echo off
echo ============================================================
echo  OnBid Auction Finder - Windows Boot Autostart Setup
echo ============================================================
echo.
echo This script registers the server to run automatically in the
echo background when Windows boots up. (Requires Admin Privileges)
echo.

:: Check for administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator.
    echo Please right-click this file and select 'Run as Administrator'.
    pause
    exit /b
)

:: Delete existing task if it exists
schtasks /delete /tn "Onbid_Server_Autostart" /f 2>nul

:: Create task (Runs at startup under SYSTEM account, hidden)
schtasks /create /tn "Onbid_Server_Autostart" /tr "wscript.exe C:\antigravity\onbid-auction-finder\run_server_hidden.vbs" /sc onstart /ru "SYSTEM" /f

if %errorLevel% eq 0 (
    echo ============================================================
    echo  Task registration successful!
    echo  - Task Name: Onbid_Server_Autostart
    echo  - Trigger: At system startup (boot/reboot)
    echo  - Run as: SYSTEM (runs hidden in background)
    echo ============================================================
) else (
    echo [ERROR] Failed to register task.
)
pause
