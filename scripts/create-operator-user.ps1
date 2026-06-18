param(
    [string]$UserName = "KioskOperator",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

function Decode-Text([string]$Base64) {
    return [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($Base64))
}

function Write-Ru([string]$Base64, [object[]]$Arguments = @()) {
    $Text = Decode-Text $Base64
    if ($Arguments.Count -gt 0) {
        $Text = [System.String]::Format($Text, $Arguments)
    }
    Write-Host $Text
}

if (-not $Apply) {
    Write-Ru "RFJZLVJVTjog0LHRg9C00LXRgiDRgdC+0LfQtNCw0L3QsCDQuNC70Lgg0L/RgNC+0LLQtdGA0LXQvdCwINC70L7QutCw0LvRjNC90LDRjyDRg9GH0LXRgtC90LDRjyDQt9Cw0L/QuNGB0Ywg0L7Qv9C10YDQsNGC0L7RgNCwINCx0LXQtyDQv9GA0LDQsiDQsNC00LzQuNC90LjRgdGC0YDQsNGC0L7RgNCwOiB7MH0=" @($UserName)
    Write-Ru "0JfQsNC/0YPRgdC60LDQudGC0LUg0YEgLUFwcGx5INGC0L7Qu9GM0LrQviDQv9C+0YHQu9C1INC/0YDQvtCy0LXRgNC60Lgg0L/Qu9Cw0L3QsCDQuCByZXN0b3JlLg=="
    exit 0
}

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    throw (Decode-Text "0J3Rg9C20L3RiyDQv9GA0LDQstCwINCw0LTQvNC40L3QuNGB0YLRgNCw0YLQvtGA0LAu")
}

if (Get-Command New-LocalUser -ErrorAction SilentlyContinue) {
    if (-not (Get-LocalUser -Name $UserName -ErrorAction SilentlyContinue)) {
        $prompt = [System.String]::Format((Decode-Text "0J/QsNGA0L7Qu9GMINC00LvRjyB7MH0="), $UserName)
        $password = Read-Host $prompt -AsSecureString
        $description = Decode-Text "0J7Qv9C10YDQsNGC0L7RgCBQeXRob25LaW9zaw=="
        New-LocalUser -Name $UserName -Password $password -Description $description
    }
    Remove-LocalGroupMember -Group "Administrators" -Member $UserName -ErrorAction SilentlyContinue
} else {
    Write-Ru "0J7QsdC90LDRgNGD0LbQtdC90LAgbGVnYWN5LdGB0LjRgdGC0LXQvNCwLiDQodC+0LfQtNCw0LnRgtC1INC/0L7Qu9GM0LfQvtCy0LDRgtC10LvRjyDQstGA0YPRh9C90YPRjiDRh9C10YDQtdC3IENvbXB1dGVyIE1hbmFnZW1lbnQg0LjQu9C4ICduZXQgdXNlcicu"
}
