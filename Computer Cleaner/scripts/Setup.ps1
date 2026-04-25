param(
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

Push-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
Pop-Location

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

Write-Host "Project root: $ProjectRoot"

& $PythonExe --version

if (-not (Test-Path -LiteralPath ".\\venv")) {
  & $PythonExe -m venv venv
}

& ".\\venv\\Scripts\\Activate.ps1"

python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Setup complete."

