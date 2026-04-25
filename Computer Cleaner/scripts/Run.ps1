param(
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath ".\\venv\\Scripts\\Activate.ps1")) {
  throw "Missing venv. Run scripts\\Setup.ps1 first."
}

& ".\\venv\\Scripts\\Activate.ps1"
& $PythonExe App.py

