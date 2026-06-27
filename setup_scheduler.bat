@echo off
echo ============================================================
echo  Onbid Auto Sync - Windows Task Scheduler Setup
echo  Schedule: 00:00 (Midnight), 12:00 (Noon), 18:00 (Evening) daily
echo ============================================================

rem 기존 태스크 삭제 (없으면 에러 무시)
schtasks /delete /tn "Onbid_Auction_Sync_AM" /f 2>nul
schtasks /delete /tn "Onbid_Auction_Sync_PM" /f 2>nul
schtasks /delete /tn "Onbid_Auction_Sync_0000" /f 2>nul
schtasks /delete /tn "Onbid_Auction_Sync_1200" /f 2>nul
schtasks /delete /tn "Onbid_Auction_Sync_1800" /f 2>nul

rem 00:00 - 자정 동기화
schtasks /create /tn "Onbid_Auction_Sync_0000" /tr "wscript.exe C:\antigravity\onbid-auction-finder\run_hidden.vbs" /sc daily /st 00:00 /ru "SYSTEM" /f

rem 12:00 - 점심 동기화
schtasks /create /tn "Onbid_Auction_Sync_1200" /tr "wscript.exe C:\antigravity\onbid-auction-finder\run_hidden.vbs" /sc daily /st 12:00 /ru "SYSTEM" /f

rem 18:00 - 저녁 동기화
schtasks /create /tn "Onbid_Auction_Sync_1800" /tr "wscript.exe C:\antigravity\onbid-auction-finder\run_hidden.vbs" /sc daily /st 18:00 /ru "SYSTEM" /f

echo ============================================================
echo  Task registration complete!
echo  - Onbid_Auction_Sync_0000 : 매일 00:00 (자정)
echo  - Onbid_Auction_Sync_1200 : 매일 12:00 (점심)
echo  - Onbid_Auction_Sync_1800 : 매일 18:00 (저녁)
echo ============================================================
pause
