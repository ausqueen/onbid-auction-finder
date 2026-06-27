Set WshShell = CreateObject("WScript.Shell")
' 0 option runs the window hidden
WshShell.Run chr(34) & "C:\antigravity\onbid-auction-finder\start_background.bat" & Chr(34), 0
Set WshShell = Nothing
