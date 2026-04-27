param(
  [switch]$AutoSetup
)

$ErrorActionPreference = "Stop"

try {
  $RepoRoot = (Resolve-Path $PSScriptRoot).Path | Split-Path -Parent
  $ProjectScript = Join-Path $RepoRoot "Computer Cleaner\scripts\Run.ps1"
  if (-not (Test-Path -LiteralPath $ProjectScript)) {
    throw "Project launcher not found at $ProjectScript"
  }

  & $ProjectScript -AutoSetup:$AutoSetup
}
catch {
  Write-Host ""
  Write-Host "Root launcher failed:" -ForegroundColor Red
  Write-Host $_.Exception.Message -ForegroundColor Red
  throw
}
