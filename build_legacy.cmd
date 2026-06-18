@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if not defined PYTHON27 set "PYTHON27=C:\Python27\python.exe"
if not exist "%PYTHON27%" (
    echo Python 2.7 x86 not found: %PYTHON27%
    echo Set PYTHON27 to the full path of python.exe.
    exit /b 2
)

"%PYTHON27%" -c "import struct,sys; ok=sys.version_info[:2]==(2,7) and struct.calcsize('P')*8==32; sys.stdout.write('Python 2.7 x86: %%s\n' %% ok); sys.exit(0 if ok else 2)"
if errorlevel 1 exit /b 2

"%PYTHON27%" -m unittest discover -s legacy_tests
if errorlevel 1 exit /b 3

"%PYTHON27%" -m pip --version >nul 2>&1
if errorlevel 1 (
    "%PYTHON27%" -m ensurepip --default-pip
    if errorlevel 1 exit /b 4
)

set "PACKAGES=%CD%\build-legacy-packages"
if exist "%PACKAGES%" rmdir /s /q "%PACKAGES%"
mkdir "%PACKAGES%"

if defined LEGACY_WHEELHOUSE (
    "%PYTHON27%" -m pip install --disable-pip-version-check --no-deps --no-index --find-links "%LEGACY_WHEELHOUSE%" --target "%PACKAGES%" -r requirements-legacy-build.txt
) else (
    "%PYTHON27%" -m pip install --disable-pip-version-check --no-deps --target "%PACKAGES%" -r requirements-legacy-build.txt
)
if errorlevel 1 exit /b 5

set "PYTHONPATH=%PACKAGES%;%PACKAGES%\win32;%PACKAGES%\win32\lib"
set "PATH=%PACKAGES%\pywin32_system32;%PATH%"
"%PYTHON27%" -m PyInstaller --clean --noconfirm --workpath build-legacy --distpath dist-legacy RezhimKioska.Legacy.spec
if errorlevel 1 exit /b 6

if exist "release\legacy" rmdir /s /q "release\legacy"
mkdir "release\legacy\config"
copy /y "dist-legacy\RezhimKioska-Legacy.exe" "release\legacy\RezhimKioska-Legacy.exe" >nul
copy /y "config\kiosk.legacy.json" "release\legacy\config\kiosk.json" >nul

echo Built release\legacy\RezhimKioska-Legacy.exe
exit /b 0
