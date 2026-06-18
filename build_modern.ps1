param(
    [string]$PythonExe = "C:\Python38-32\python.exe",
    [string]$Wheelhouse = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $MyInvocation.MyCommand.Path))
$RequirementsPath = Join-Path $ProjectRoot "requirements-modern-build.txt"
$SpecPath = Join-Path $ProjectRoot "RezhimKioska.Modern.spec"
$WorkDir = Join-Path $ProjectRoot "build-modern"
$DistDir = Join-Path $ProjectRoot "dist-modern"
$ReleaseDir = Join-Path $ProjectRoot "release"
$TargetDir = Join-Path $ReleaseDir "modern"
$StageDir = Join-Path $ReleaseDir "modern.tmp"

function Assert-ProjectPath([string]$Path) {
    $Resolved = [System.IO.Path]::GetFullPath($Path)
    if (-not $Resolved.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Build path is outside the project: $Resolved"
    }
}

foreach ($Path in @($WorkDir, $DistDir, $ReleaseDir, $TargetDir, $StageDir)) {
    Assert-ProjectPath $Path
}

if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "Python 3.8 x86 was not found: $PythonExe"
}

$RuntimeJson = & $PythonExe -c "import json,struct,sys; print(json.dumps({'version': list(sys.version_info[:2]), 'bits': struct.calcsize('P') * 8}))"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect the selected Python runtime."
}
$Runtime = $RuntimeJson | ConvertFrom-Json
if ($Runtime.version[0] -ne 3 -or $Runtime.version[1] -ne 8) {
    throw "Modern build requires Python 3.8 exactly."
}
if ($Runtime.bits -ne 32) {
    throw "Modern build requires a 32-bit Python runtime."
}

Set-Location $ProjectRoot

if ($Wheelhouse) {
    $Wheelhouse = [System.IO.Path]::GetFullPath($Wheelhouse)
    if (-not (Test-Path -LiteralPath $Wheelhouse -PathType Container)) {
        throw "Modern wheelhouse was not found: $Wheelhouse"
    }
    & $PythonExe -m pip install --disable-pip-version-check --no-index --find-links $Wheelhouse -r $RequirementsPath
} else {
    & $PythonExe -m pip install --disable-pip-version-check -r $RequirementsPath
}
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install Modern build dependencies."
}

& $PythonExe -m unittest discover tests
if ($LASTEXITCODE -ne 0) {
    throw "Modern tests failed; the executable was not built."
}

foreach ($Path in @($WorkDir, $DistDir, $StageDir)) {
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

& $PythonExe -m PyInstaller --noconfirm --clean --workpath $WorkDir --distpath $DistDir $SpecPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed to build RezhimKioska-Modern.exe."
}

$BuiltExe = Join-Path $DistDir "RezhimKioska-Modern.exe"
if (-not (Test-Path -LiteralPath $BuiltExe -PathType Leaf)) {
    throw "Modern executable was not produced: $BuiltExe"
}

New-Item -ItemType Directory -Force -Path (Join-Path $StageDir "config") | Out-Null
Copy-Item -LiteralPath $BuiltExe -Destination (Join-Path $StageDir "RezhimKioska-Modern.exe") -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "config\kiosk.json") -Destination (Join-Path $StageDir "config\kiosk.json") -Force

if (-not (Test-Path -LiteralPath $ReleaseDir)) {
    New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
}
if (Test-Path -LiteralPath $TargetDir) {
    Remove-Item -LiteralPath $TargetDir -Recurse -Force
}
Move-Item -LiteralPath $StageDir -Destination $TargetDir

Write-Host "Modern build ready: $TargetDir"
