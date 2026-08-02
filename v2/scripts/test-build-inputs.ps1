param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Modern", "Legacy")]
    [string]$Family,
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"
if (-not $ProjectRoot) {
    $ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
} else {
    $ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
}

$familyName = $Family.ToLowerInvariant()
$requiredPaths = @(
    "config\kiosk.v2.default.json",
    "v2\contracts\kiosk-config-v2.schema.json",
    "v2\scripts\write-sha256.ps1",
    "v2\$familyName\launcher_main.py",
    "v2\$familyName\restore_main.py",
    "v2\$familyName\configurator_main.py",
    "v2\build\$familyName-launcher.spec",
    "v2\build\$familyName-restore.spec",
    "v2\build\$familyName-configurator.spec"
)

$missingPaths = @()
foreach ($relativePath in $requiredPaths) {
    $fullPath = Join-Path $ProjectRoot $relativePath
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        $missingPaths += $relativePath
    }
}

if ($missingPaths.Count -gt 0) {
    $details = ($missingPaths | ForEach-Object { "  - $_" }) -join [Environment]::NewLine
    throw "Build input validation failed for $Family. Missing required file(s):$([Environment]::NewLine)$details"
}

Write-Host "Build input validation passed for $Family ($($requiredPaths.Count) files)."
