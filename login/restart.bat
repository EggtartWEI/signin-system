@echo off
setlocal
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Stopping service...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'attendance_login_only\.py' } | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop; Write-Host ('Stopped PID ' + $_.ProcessId) } catch {} }"

timeout /t 1 /nobreak >nul

echo Initializing whitelist...
python scripts\init_whitelist.py

echo Starting service...
python attendance_login_only.py

endlocal
