@echo off
setlocal
if "%~1"=="" (
  echo Usage: restore-legacy.cmd RestoreLegacy.exe
  exit /b 2
)
"%~1" restore
exit /b %ERRORLEVEL%
