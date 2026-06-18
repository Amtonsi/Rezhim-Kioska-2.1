param(
    [string]$Config = "$PSScriptRoot\..\config\kiosk.json",
    [string]$StateDir = "",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
Set-Location $ProjectRoot

if ($Apply) {
    if ($StateDir) {
        python main.py install --config $Config --state-dir $StateDir --apply
    } else {
        python main.py install --config $Config --apply
    }
} else {
    if ($StateDir) {
        python main.py install --config $Config --state-dir $StateDir
    } else {
        python main.py install --config $Config
    }
}
