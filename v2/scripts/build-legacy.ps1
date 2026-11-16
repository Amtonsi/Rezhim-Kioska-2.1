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
$stagingDistPath = Join-Path $projectRoot "v2\build\dist-legacy-onedir"
$workLauncher = Join-Path $projectRoot "v2\build\work-legacy-launcher"
$workRestore = Join-Path $projectRoot "v2\build\work-legacy-restore"
$workConfigurator = Join-Path $projectRoot "v2\build\work-legacy-configurator"

& (Join-Path $PSScriptRoot "test-build-inputs.ps1") `
    -Family Legacy -ProjectRoot $projectRoot

function Reset-ProjectDirectory {
    param([string]$Path)

    $fullPath = [IO.Path]::GetFullPath($Path)
    $safeRoot = [IO.Path]::GetFullPath($projectRoot)
    if (-not $fullPath.StartsWith($safeRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clear path outside project root: $fullPath"
    }
    if (Test-Path -LiteralPath $fullPath) {
        Remove-Item -LiteralPath $fullPath -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $fullPath | Out-Null
}

function Merge-LegacyOnedirOutput {
    param([string]$Name)

    $sourceDirectory = Join-Path $stagingDistPath $Name
    $sourceExecutable = Join-Path $sourceDirectory "$Name.exe"
    if (-not (Test-Path -LiteralPath $sourceExecutable -PathType Leaf)) {
        throw "Legacy onedir executable was not produced: $sourceExecutable"
    }

    Get-ChildItem -LiteralPath $sourceDirectory -Force | ForEach-Object {
        $destination = Join-Path $distPath $_.Name
        Copy-Item -LiteralPath $_.FullName -Destination $destination -Recurse -Force
    }
}

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

    & $Python -m unittest discover -s "v2\tests\legacy" -p "test_*.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Legacy unit tests failed; build was not started."
    }
    & $Python -m unittest discover -s "v2\tests" -p "test_build_contract.py"
    if ($LASTEXITCODE -ne 0) {
        throw "V2 build contract tests failed; build was not started."
    }

    Reset-ProjectDirectory -Path $distPath
    Reset-ProjectDirectory -Path $stagingDistPath

    & $Python -m PyInstaller --noconfirm --clean `
        --distpath $stagingDistPath --workpath $workLauncher `
        "v2\build\legacy-launcher.spec"
    if ($LASTEXITCODE -ne 0) { throw "Legacy launcher build failed." }

    & $Python -m PyInstaller --noconfirm --clean `
        --distpath $stagingDistPath --workpath $workRestore `
        "v2\build\legacy-restore.spec"
    if ($LASTEXITCODE -ne 0) { throw "Legacy Restore build failed." }

    & $Python -m PyInstaller --noconfirm --clean `
        --distpath $stagingDistPath --workpath $workConfigurator `
        "v2\build\legacy-configurator.spec"
    if ($LASTEXITCODE -ne 0) { throw "Legacy Configurator build failed." }

    Merge-LegacyOnedirOutput -Name "RezhimKioska-V2-Legacy"
    Merge-LegacyOnedirOutput -Name "Restore-V2-Legacy"
    Merge-LegacyOnedirOutput -Name "Configurator-V2-Legacy"

    $configDirectory = Join-Path $distPath "config"
    New-Item -ItemType Directory -Force -Path $configDirectory | Out-Null
    Copy-Item -LiteralPath "config\kiosk.v2.default.json" `
        -Destination (Join-Path $configDirectory "kiosk.v2.json") -Force
    Copy-Item -LiteralPath (Join-Path $distPath "Restore-V2-Legacy.exe") `
        -Destination (Join-Path $distPath "Restore.exe") -Force
    Copy-Item -LiteralPath (Join-Path $distPath "Configurator-V2-Legacy.exe") `
        -Destination (Join-Path $distPath "Configurator.exe") -Force
    $readmePath = Join-Path $distPath "LEGACY-XP-README.txt"
    $readmeLines = @(
        "Legacy package for Windows XP / Server 2003 x86. See the published test matrix.",
        "",
        "Keep all files in this folder together. Do not copy only the EXE.",
        "Run RezhimKioska-V2-Legacy.exe from this folder.",
        "Modern build is separate and is not required for this legacy package."
    )
    $asciiEncoding = New-Object System.Text.ASCIIEncoding
    [IO.File]::WriteAllLines($readmePath, $readmeLines, $asciiEncoding)
    & (Join-Path $PSScriptRoot "write-sha256.ps1") -ProjectRoot $projectRoot
}
finally {
    Pop-Location
    $env:PYTHONPATH = $oldPythonPath
    $env:PATH = $oldPath
}
