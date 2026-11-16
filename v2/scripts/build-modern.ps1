param(
    [string]$Python = "$env:LOCALAPPDATA\Python38-32\python.exe",
    [ValidateSet("compat-x86", "current-x64")][string]$Target = "compat-x86"
)

$ErrorActionPreference = "Stop"
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$distPath = Join-Path $projectRoot "v2\dist\modern"
if ($Target -eq "current-x64") {
    $distPath = Join-Path $projectRoot "v2\dist\modern-x64"
}
$workLauncher = Join-Path $projectRoot "v2\build\work-$Target-launcher"
$workRestore = Join-Path $projectRoot "v2\build\work-$Target-restore"
$workConfigurator = Join-Path $projectRoot "v2\build\work-$Target-configurator"

& (Join-Path $PSScriptRoot "test-build-inputs.ps1") `
    -Family Modern -ProjectRoot $projectRoot

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python for $Target was not found: $Python"
}

Push-Location $projectRoot
try {
    $expected = if ($Target -eq "current-x64") { "3.14-64" } else { "3.8-32" }
    & $Python -c "import struct, sys, PyInstaller; actual = '%d.%d-%d' % (sys.version_info[0], sys.version_info[1], 8 * struct.calcsize('P')); sys.exit(0 if actual == sys.argv[1] and PyInstaller.__version__ == '6.22.3' else 1)" $expected
    if ($LASTEXITCODE -ne 0) {
        throw "$Target requires Python $expected and PyInstaller 6.22.3."
    }

    & $Python -m unittest discover -s "v2\tests\modern" -p "test_*.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Modern unit tests failed; build was not started."
    }
    & $Python -m unittest discover -s "v2\tests" -p "test_build_contract.py"
    if ($LASTEXITCODE -ne 0) {
        throw "V2 build contract tests failed; build was not started."
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
