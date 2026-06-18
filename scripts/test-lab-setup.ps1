param(
    [string]$UserName = "KioskOperator"
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

Write-Ru "0KfQtdC6LdC70LjRgdGCINCx0LXQt9C+0L/QsNGB0L3QvtC5INC70LDQsdC+0YDQsNGC0L7RgNC90L7QuSDQv9GA0L7QstC10YDQutC4Og=="
Write-Ru "MS4g0JjRgdC/0L7Qu9GM0LfRg9C50YLQtSDQvtGC0LTQtdC70YzQvdGD0Y4g0LvQvtC60LDQu9GM0L3Rg9GOINGD0YfQtdGC0L3Rg9GOINC30LDQv9C40YHRjCDQvtC/0LXRgNCw0YLQvtGA0LAg0LHQtdC3INC/0YDQsNCyINCw0LTQvNC40L3QuNGB0YLRgNCw0YLQvtGA0LA6IHswfQ==" @($UserName)
Write-Ru "Mi4g0J3QtSDQv9GA0LjQvNC10L3Rj9C50YLQtSDQvdCw0YHRgtGA0L7QudC60Lgg0LrQuNC+0YHQutCwINC6INC+0YHQvdC+0LLQvdC+0Lkg0YPRh9C10YLQvdC+0Lkg0LfQsNC/0LjRgdC4Lg=="
Write-Ru "My4g0KHQvdCw0YfQsNC70LAg0LfQsNC/0YPRgdGC0LjRgtC1IGluc3RhbGwucHMxINCx0LXQtyAtQXBwbHku"
Write-Ru "NC4g0JTQviDQv9GA0LjQvNC10L3QtdC90LjRjyDQv9GA0L7QstC10YDRjNGC0LUg0LLRi9Cy0L7QtCByZXN0b3JlLnBzMSDQsiBkcnktcnVuLg=="
Write-Ru "NS4g0JTQtdGA0LbQuNGC0LUg0LTQvtGB0YLRg9C/0L3QvtC5INCw0LTQvNC40L3QuNGB0YLRgNCw0YLQuNCy0L3Rg9GOINGD0YfQtdGC0L3Rg9GOINC30LDQv9C40YHRjCDQtNC70Y8g0L7RgtC60LDRgtCwLg=="
