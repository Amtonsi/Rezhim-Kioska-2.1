param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [Parameter(Mandatory = $true)][string]$Config,
    [Parameter(Mandatory = $true)][string]$LauncherCommand,
    [ValidateSet("install", "repair", "dry-run", "test-mode")][string]$Command = "dry-run",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$arguments = @($Command, "--config", $Config, "--launcher-command", $LauncherCommand)
if ($Apply) {
    $arguments += "--apply"
}
& $Executable @arguments
exit $LASTEXITCODE
