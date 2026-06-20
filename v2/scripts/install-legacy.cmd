@echo off
setlocal
if "%~3"=="" (
  echo Usage: install-legacy.cmd KioskLegacy.exe kiosk.json "launcher command"
  exit /b 2
)
"%~1" dry-run --config "%~2" --launcher-command "%~3"
exit /b %ERRORLEVEL%
