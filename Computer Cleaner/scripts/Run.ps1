param(
  [switch]$AutoSetup
)

$ErrorActionPreference = "Stop"

try {
  $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  $VenvDir = Join-Path $ProjectRoot "venv"
  $VenvActivate = Join-Path $VenvDir "Scripts\Activate.ps1"
  $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
  $AppPath = Join-Path $ProjectRoot "App.py"
  $RequirementsPath = Join-Path $ProjectRoot "requirements.txt"
  $LogDir = Join-Path $ProjectRoot "data\logs"
  $StdOutPath = Join-Path $LogDir "launcher-output.log"
  $StdErrPath = Join-Path $LogDir "launcher-error.log"

  Write-Output "Current directory: $(Get-Location)"
  Write-Output "Project root: $ProjectRoot"
  Write-Output "Venv activate: $VenvActivate"
  Write-Output "Python: $VenvPython"
  Write-Output "App: $AppPath"
  Write-Output "Requirements: $RequirementsPath"

  if (-not (Test-Path -LiteralPath $RequirementsPath)) {
    throw "requirements.txt not found at $RequirementsPath"
  }

  if (-not (Test-Path -LiteralPath $AppPath)) {
    throw "App.py not found at $AppPath"
  }

  if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "python.exe not found at $VenvPython"
  }

  if (-not (Test-Path -LiteralPath $VenvActivate)) {
    throw "Activate.ps1 not found at $VenvActivate"
  }

  Set-Location -LiteralPath $ProjectRoot
  New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
  Remove-Item -LiteralPath $StdOutPath, $StdErrPath -Force -ErrorAction SilentlyContinue

  . $VenvActivate
  $ActivatedPython = (Get-Command python).Source
  Write-Output "Activated python: $ActivatedPython"

  $process = Start-Process -FilePath $ActivatedPython -ArgumentList @("-u", ('"' + $AppPath + '"')) -WorkingDirectory $ProjectRoot -PassThru -RedirectStandardOutput $StdOutPath -RedirectStandardError $StdErrPath

  Start-Sleep -Seconds 2
  if ($process.HasExited) {
    $stdout = if (Test-Path -LiteralPath $StdOutPath) { Get-Content -LiteralPath $StdOutPath -Raw } else { "" }
    $stderr = if (Test-Path -LiteralPath $StdErrPath) { Get-Content -LiteralPath $StdErrPath -Raw } else { "" }
    if ($stdout) {
      Write-Output $stdout
    }
    if ($stderr) {
      Write-Error $stderr
    }
    throw "App exited immediately with code $($process.ExitCode)."
  }

  Write-Output "App launched successfully. PID: $($process.Id)"

}
catch {
  Write-Output ""
  Write-Error "Launcher failed: $($_.Exception.Message)"
  throw
}
