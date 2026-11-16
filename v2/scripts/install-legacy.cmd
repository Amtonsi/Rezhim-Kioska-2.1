@echo off
setlocal
if "%~3"=="" (
  echo Usage: install-legacy.cmd Restore.exe kiosk.json "full path to RezhimKioska-V2-Legacy.exe"
  exit /b 2
)
"%~1" dry-run --config "%~2" --launcher-command "%~3"
exit /b %ERRORLEVEL%
