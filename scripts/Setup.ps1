param(
  [switch]$Quiet
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path $PSScriptRoot).Path | Split-Path -Parent
$ProjectScripts = Join-Path $RepoRoot "Computer Cleaner\scripts\Setup.ps1"

& $ProjectScripts -Quiet:$Quiet

