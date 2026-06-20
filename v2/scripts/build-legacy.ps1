param(
    [string]$Python = "$env:LOCALAPPDATA\Python27-x86-portable\python.exe",
    [string]$Toolchain = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
if (-not $Toolchain) {
    $Toolchain = Join-Path $projectRoot "v2\toolchain\pyinstaller-3.2.1"
}
$Toolchain = [IO.Path]::GetFullPath($Toolchain)
$distPath = Join-Path $projectRoot "v2\dist\legacy"
$workLauncher = Join-Path $projectRoot "v2\build\work-legacy-launcher"
$workRestore = Join-Path $projectRoot "v2\build\work-legacy-restore"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python 2.7 x86 was not found: $Python"
}
if (-not (Test-Path -LiteralPath (Join-Path $Toolchain "PyInstaller\__main__.py"))) {
    throw "Legacy PyInstaller toolchain was not found: $Toolchain"
}

$oldPythonPath = $env:PYTHONPATH
$oldPath = $env:PATH
$env:PYTHONPATH = @(
    $Toolchain,
    (Join-Path $Toolchain "win32"),
    (Join-Path $Toolchain "win32\lib"),
    (Join-Path $Toolchain "Pythonwin")
) -join ";"
$env:PATH = (Join-Path $Toolchain "pywin32_system32") + ";" + $env:PATH

Push-Location $projectRoot
try {
    & $Python -c "import struct, pywintypes, win32api; raise SystemExit(0 if struct.calcsize('P') == 4 else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw "Legacy build requires Python 2.7 x86 and the local pywin32 runtime."
    }

    & $Python -m PyInstaller --noconfirm --clean `
        --distpath $distPath --workpath $workLauncher `
        "v2\build\legacy-launcher.spec"
    if ($LASTEXITCODE -ne 0) { throw "Legacy launcher build failed." }

    & $Python -m PyInstaller --noconfirm --clean `
        --distpath $distPath --workpath $workRestore `
        "v2\build\legacy-restore.spec"
    if ($LASTEXITCODE -ne 0) { throw "Legacy Restore build failed." }

    $configDirectory = Join-Path $distPath "config"
    New-Item -ItemType Directory -Force -Path $configDirectory | Out-Null
    Copy-Item -LiteralPath "config\kiosk.v2.default.json" `
        -Destination (Join-Path $configDirectory "kiosk.v2.json") -Force
    Copy-Item -LiteralPath (Join-Path $distPath "Restore-V2-Legacy.exe") `
        -Destination (Join-Path $distPath "Restore.exe") -Force
}
finally {
    Pop-Location
    $env:PYTHONPATH = $oldPythonPath
    $env:PATH = $oldPath
}
