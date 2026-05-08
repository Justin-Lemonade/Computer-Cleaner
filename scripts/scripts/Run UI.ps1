param(
  [switch]$AutoSetup
)

$ErrorActionPreference = "Stop"

try {
  $ParentLauncher = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path "Run UI.ps1"
  if (-not (Test-Path -LiteralPath $ParentLauncher)) {
    throw "Parent launcher not found at $ParentLauncher"
  }

  & $ParentLauncher -AutoSetup:$AutoSetup
}
catch {
  Write-Host ""
  Write-Host "Compatibility launcher failed:" -ForegroundColor Red
  Write-Host $_.Exception.Message -ForegroundColor Red
  throw
}
