Set WshShell = CreateObject("WScript.Shell")
' 0은 창을 숨긴 채(히든 모드)로 실행하라는 옵션입니다.
WshShell.Run chr(34) & "C:\antigravity\onbid-auction-finder\run_all_sync.bat" & Chr(34), 0
Set WshShell = Nothing
