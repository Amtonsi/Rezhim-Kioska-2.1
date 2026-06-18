$ErrorActionPreference = "Stop"

# Builds "Режим киоска" into an exe and prepares a GitHub archive.
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ReleaseDir = Join-Path $ProjectRoot "release"
$StageDir = Join-Path $ReleaseDir "github"
$ArchivePath = Join-Path $ReleaseDir "PythonKiosk-GitHub.zip"
$ResolvedProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$ResolvedReleaseDir = [System.IO.Path]::GetFullPath($ReleaseDir)
$ResolvedStageDir = [System.IO.Path]::GetFullPath($StageDir)

if (-not $ResolvedReleaseDir.StartsWith($ResolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The release directory must stay inside the project."
}
if (-not $ResolvedStageDir.StartsWith($ResolvedReleaseDir, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The staging directory must stay inside release."
}

Set-Location $ProjectRoot

python -m PyInstaller --noconfirm --clean "$ProjectRoot\RezhimKioska.spec"

if (Test-Path $ReleaseDir) {
    Remove-Item -LiteralPath $ReleaseDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
New-Item -ItemType Directory -Force -Path $StageDir | Out-Null

Copy-Item -LiteralPath "$ProjectRoot\dist\RezhimKioska.exe" -Destination "$ReleaseDir\RezhimKioska.exe" -Force
New-Item -ItemType Directory -Force -Path "$ReleaseDir\config" | Out-Null
Copy-Item -LiteralPath "$ProjectRoot\config\kiosk.json" -Destination "$ReleaseDir\config\kiosk.json" -Force

$ArchiveFiles = @(
    "main.py",
    "RezhimKioska.spec",
    "requirements-build.txt",
    "README.md",
    "build_release.ps1"
)

foreach ($Item in $ArchiveFiles) {
    Copy-Item -LiteralPath "$ProjectRoot\$Item" -Destination "$StageDir\$Item" -Force
}

foreach ($Dir in @("python_kiosk", "tests", "docs", "config", "scripts", "src")) {
    Copy-Item -LiteralPath "$ProjectRoot\$Dir" -Destination "$StageDir\$Dir" -Recurse -Force
}

New-Item -ItemType Directory -Force -Path "$StageDir\dist" | Out-Null
Copy-Item -LiteralPath "$ProjectRoot\dist\RezhimKioska.exe" -Destination "$StageDir\dist\RezhimKioska.exe" -Force

Get-ChildItem -LiteralPath $StageDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $StageDir -Recurse -File |
    Where-Object { $_.Extension -eq ".pyc" -or $_.Extension -eq ".pyo" } |
    Remove-Item -Force

Compress-Archive -Path "$StageDir\*" -DestinationPath $ArchivePath -Force
Write-Host "Done: $ArchivePath"
