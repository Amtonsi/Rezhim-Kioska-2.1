param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [ValidateSet("restore", "uninstall", "recover-desktop")][string]$Command = "restore",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$arguments = @($Command)
if ($Apply) {
    $arguments += "--apply"
}
& $Executable @arguments
exit $LASTEXITCODE
