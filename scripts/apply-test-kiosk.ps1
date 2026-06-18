$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\impal\PycharmProjects\PythonKiosk"
$ExePath = Join-Path $ProjectRoot "release\RezhimKioska.exe"
$ConfigPath = Join-Path $ProjectRoot "config\kiosk.json"
$LogPath = Join-Path $ProjectRoot "apply-test-kiosk.log"

function Write-Step {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    $line | Tee-Object -FilePath $LogPath -Append
}

Write-Step "=== apply-test-kiosk started ==="
Write-Step "ProjectRoot: $ProjectRoot"
Write-Step "ExePath: $ExePath"
Write-Step "ConfigPath: $ConfigPath"

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Step "ERROR: elevated administrator rights are required."
    throw "Отказано в доступе. Для выполнения действия требуются права администратора Windows."
}

if (-not (Test-Path -LiteralPath $ExePath)) {
    Write-Step "ERROR: exe not found."
    throw "Exe not found: $ExePath"
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    Write-Step "ERROR: config not found."
    throw "Config not found: $ConfigPath"
}

Write-Step "Running install --apply for operator test."
& $ExePath install --config $ConfigPath --apply 2>&1 | Tee-Object -FilePath $LogPath -Append
if ($LASTEXITCODE -ne 0) {
    Write-Step "ERROR: install failed with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}

Write-Step "Current sessions before optional test logoff:"
query user 2>&1 | Tee-Object -FilePath $LogPath -Append

$testSession = (query user 2>$null | Select-String -Pattern "^\s*test\s+|^\s*>\s*test\s+").ToString()
if ($testSession) {
    $parts = $testSession -split "\s+"
    $sessionId = $null
    foreach ($part in $parts) {
        if ($part -match "^\d+$") {
            $sessionId = $part
        }
    }
    if ($sessionId) {
        Write-Step "Logging off test session id $sessionId so the next login starts the new shell."
        logoff $sessionId 2>&1 | Tee-Object -FilePath $LogPath -Append
    }
}

Write-Step "Current sessions after apply:"
query user 2>&1 | Tee-Object -FilePath $LogPath -Append
Write-Step "=== apply-test-kiosk finished ==="
