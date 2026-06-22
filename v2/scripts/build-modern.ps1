param(
    [string]$Python = "$env:LOCALAPPDATA\Python38-32\python.exe"
)

$ErrorActionPreference = "Stop"
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$distPath = Join-Path $projectRoot "v2\dist\modern"
$workLauncher = Join-Path $projectRoot "v2\build\work-modern-launcher"
$workRestore = Join-Path $projectRoot "v2\build\work-modern-restore"
$workConfigurator = Join-Path $projectRoot "v2\build\work-modern-configurator"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python 3.8 x86 was not found: $Python"
}

Push-Location $projectRoot
try {
    & $Python -c "import struct; raise SystemExit(0 if struct.calcsize('P') == 4 else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw "Modern build requires 32-bit Python."
    }

    & $Python -m PyInstaller --noconfirm --clean `
        --distpath $distPath --workpath $workLauncher `
        "v2\build\modern-launcher.spec"
    if ($LASTEXITCODE -ne 0) { throw "Modern launcher build failed." }

    & $Python -m PyInstaller --noconfirm --clean `
        --distpath $distPath --workpath $workRestore `
        "v2\build\modern-restore.spec"
    if ($LASTEXITCODE -ne 0) { throw "Modern Restore build failed." }

    & $Python -m PyInstaller --noconfirm --clean `
        --distpath $distPath --workpath $workConfigurator `
        "v2\build\modern-configurator.spec"
    if ($LASTEXITCODE -ne 0) { throw "Modern Configurator build failed." }

    $configDirectory = Join-Path $distPath "config"
    New-Item -ItemType Directory -Force -Path $configDirectory | Out-Null
    Copy-Item -LiteralPath "config\kiosk.v2.default.json" `
        -Destination (Join-Path $configDirectory "kiosk.v2.json") -Force
    Copy-Item -LiteralPath (Join-Path $distPath "Restore-V2-Modern.exe") `
        -Destination (Join-Path $distPath "Restore.exe") -Force
    Copy-Item -LiteralPath (Join-Path $distPath "Configurator-V2-Modern.exe") `
        -Destination (Join-Path $distPath "Configurator.exe") -Force
    & (Join-Path $PSScriptRoot "write-sha256.ps1") -ProjectRoot $projectRoot
}
finally {
    Pop-Location
}
