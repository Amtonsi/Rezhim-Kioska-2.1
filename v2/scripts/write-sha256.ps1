param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"
if (-not $ProjectRoot) {
    $ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
}

$distRoot = Join-Path $ProjectRoot "v2\dist"
$targets = @(
    "modern-x64\RezhimKioska-V2-Modern.exe",
    "modern-x64\Restore-V2-Modern.exe",
    "modern-x64\Configurator-V2-Modern.exe",
    "modern\RezhimKioska-V2-Modern.exe",
    "modern\Restore-V2-Modern.exe",
    "modern\Configurator-V2-Modern.exe",
    "legacy\RezhimKioska-V2-Legacy.exe",
    "legacy\Restore-V2-Legacy.exe",
    "legacy\Configurator-V2-Legacy.exe"
)
$lines = @()
foreach ($relativePath in $targets) {
    $path = Join-Path $distRoot $relativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        continue
    }
    $item = Get-Item -LiteralPath $path
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    $portablePath = $relativePath.Replace("\", "/")
    $lines += "${hash}  ${portablePath}  bytes=$($item.Length)"
}

$encoding = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllLines(
    (Join-Path $distRoot "SHA256SUMS.txt"),
    $lines,
    $encoding
)
