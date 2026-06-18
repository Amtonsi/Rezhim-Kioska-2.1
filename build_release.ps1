$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ReleaseDir = Join-Path $ProjectRoot "release"
$PackageDir = Join-Path $ReleaseDir "package"
$ModernExe = Join-Path $ProjectRoot "release\modern\RezhimKioska-Modern.exe"
$LegacyExe = Join-Path $ProjectRoot "release\legacy\RezhimKioska-Legacy.exe"
$ModernConfig = Join-Path $ProjectRoot "release\modern\config\kiosk.json"
$LegacyConfig = Join-Path $ProjectRoot "release\legacy\config\kiosk.json"
$RequiredArtifacts = @($ModernExe, $LegacyExe, $ModernConfig, $LegacyConfig)

$ResolvedProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$ResolvedReleaseDir = [System.IO.Path]::GetFullPath($ReleaseDir)
$ResolvedPackageDir = [System.IO.Path]::GetFullPath($PackageDir)
if (-not $ResolvedReleaseDir.StartsWith($ResolvedProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The release directory must stay inside the project."
}
if (-not $ResolvedPackageDir.StartsWith($ResolvedReleaseDir, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The package directory must stay inside release."
}

foreach ($Path in $RequiredArtifacts) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required tested artifact is missing: $Path"
    }
}

$TemporaryRoot = Join-Path $ReleaseDir (".package-temp-" + [Guid]::NewGuid().ToString("N"))
$StageDir = Join-Path $TemporaryRoot "stage"
$ArchivePath = Join-Path $TemporaryRoot "PythonKiosk-GitHub.zip"
$HashPath = Join-Path $TemporaryRoot "SHA256SUMS.txt"
$ManifestPath = Join-Path $TemporaryRoot "build-manifest.json"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

try {
    New-Item -ItemType Directory -Force -Path $StageDir | Out-Null

    $ArchiveFiles = @(
        "main.py",
        "legacy_main.py",
        "RezhimKioska.Modern.spec",
        "RezhimKioska.Legacy.spec",
        "requirements-modern-build.txt",
        "requirements-legacy-build.txt",
        "build_modern.ps1",
        "build_legacy.cmd",
        "build_release.ps1",
        "README.md"
    )
    foreach ($Item in $ArchiveFiles) {
        $Source = Join-Path $ProjectRoot $Item
        if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
            throw "Required source file is missing: $Source"
        }
        Copy-Item -LiteralPath $Source -Destination (Join-Path $StageDir $Item) -Force
    }

    $ArchiveDirectories = @(
        "python_kiosk",
        "legacy_kiosk",
        "tests",
        "legacy_tests",
        "docs",
        "contracts",
        "config",
        "scripts",
        "src"
    )
    foreach ($Directory in $ArchiveDirectories) {
        $Source = Join-Path $ProjectRoot $Directory
        if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
            throw "Required source directory is missing: $Source"
        }
        Copy-Item -LiteralPath $Source -Destination (Join-Path $StageDir $Directory) -Recurse -Force
    }

    $StageModern = Join-Path $StageDir "release\modern"
    $StageLegacy = Join-Path $StageDir "release\legacy"
    New-Item -ItemType Directory -Force -Path (Join-Path $StageModern "config") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $StageLegacy "config") | Out-Null
    Copy-Item -LiteralPath $ModernExe -Destination (Join-Path $StageModern "RezhimKioska-Modern.exe") -Force
    Copy-Item -LiteralPath $LegacyExe -Destination (Join-Path $StageLegacy "RezhimKioska-Legacy.exe") -Force
    Copy-Item -LiteralPath $ModernConfig -Destination (Join-Path $StageModern "config\kiosk.json") -Force
    Copy-Item -LiteralPath $LegacyConfig -Destination (Join-Path $StageLegacy "config\kiosk.json") -Force

    $ExcludedNames = @(".venv", "__pycache__", ".kiosk-state", "backup", ".git", ".idea")
    Get-ChildItem -LiteralPath $StageDir -Recurse -Directory |
        Where-Object { $ExcludedNames -contains $_.Name -or $_.Name -like "build-*" -or $_.Name -like "dist-*" } |
        Sort-Object FullName -Descending |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $StageDir -Recurse -File |
        Where-Object { $_.Extension -eq ".pyc" -or $_.Extension -eq ".pyo" -or $_.Name -like "*.log" } |
        Remove-Item -Force

    $ArtifactDefinitions = @(
        @{
            Name = "modern"
            Source = $ModernExe
            RelativePath = "release/modern/RezhimKioska-Modern.exe"
        },
        @{
            Name = "legacy"
            Source = $LegacyExe
            RelativePath = "release/legacy/RezhimKioska-Legacy.exe"
        }
    )
    $ManifestArtifacts = @()
    $HashLines = @()
    foreach ($Definition in $ArtifactDefinitions) {
        $Hash = Get-FileHash -LiteralPath $Definition.Source -Algorithm SHA256
        $File = Get-Item -LiteralPath $Definition.Source
        $HashLines += "{0}  {1}" -f $Hash.Hash, $Definition.RelativePath
        $ManifestArtifacts += [ordered]@{
            name = $Definition.Name
            path = $Definition.RelativePath
            sha256 = $Hash.Hash
            bytes = [long]$File.Length
        }
    }

    $Manifest = [ordered]@{
        schemaVersion = 1
        generatedAtUtc = [DateTime]::UtcNow.ToString("o")
        artifacts = $ManifestArtifacts
    }
    $ManifestJson = $Manifest | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllLines($HashPath, $HashLines, $Utf8NoBom)
    [System.IO.File]::WriteAllText($ManifestPath, $ManifestJson + [Environment]::NewLine, $Utf8NoBom)
    Copy-Item -LiteralPath $HashPath -Destination (Join-Path $StageDir "SHA256SUMS.txt") -Force
    Copy-Item -LiteralPath $ManifestPath -Destination (Join-Path $StageDir "build-manifest.json") -Force

    Compress-Archive -Path (Join-Path $StageDir "*") -DestinationPath $ArchivePath -Force
    Remove-Item -LiteralPath $StageDir -Recurse -Force

    if (Test-Path -LiteralPath $PackageDir) {
        Remove-Item -LiteralPath $PackageDir -Recurse -Force
    }
    Move-Item -LiteralPath $TemporaryRoot -Destination $PackageDir
}
catch {
    if (Test-Path -LiteralPath $TemporaryRoot) {
        Remove-Item -LiteralPath $TemporaryRoot -Recurse -Force
    }
    throw
}

Write-Host "Done: $PackageDir"
