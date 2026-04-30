param(
  [switch]$AutoSetup
)

$ErrorActionPreference = "Stop"

function Resolve-FirstExistingPath {
  param(
    [string[]]$Candidates,
    [string]$Description
  )

  foreach ($candidate in $Candidates) {
    if (Test-Path -LiteralPath $candidate) {
      return (Resolve-Path -LiteralPath $candidate).Path
    }
  }

  throw "$Description not found. Checked: $($Candidates -join ', ')"
}

try {
  $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  $VenvDir = Join-Path $ProjectRoot "venv"
  $VenvActivate = Join-Path $VenvDir "Scripts\Activate.ps1"
  $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
  $AppPath = Join-Path $ProjectRoot "App.py"
  $SetupScript = Join-Path $ProjectRoot "scripts\Setup.ps1"
  $RequirementsPath = Resolve-FirstExistingPath -Candidates @(
    (Join-Path $ProjectRoot "requirements.txt"),
    (Join-Path $ProjectRoot "Requirements.txt")
  ) -Description "requirements file"

  $LogDir = Join-Path $ProjectRoot "data\logs"
  $StdOutPath = Join-Path $LogDir "launcher-output.log"
  $StdErrPath = Join-Path $LogDir "launcher-error.log"

  Write-Output "Current directory: $(Get-Location)"
  Write-Output "Project root: $ProjectRoot"
  Write-Output "Setup script: $SetupScript"
  Write-Output "Python: $VenvPython"
  Write-Output "App: $AppPath"
  Write-Output "Requirements: $RequirementsPath"

  if (-not (Test-Path -LiteralPath $AppPath)) {
    throw "App.py not found at $AppPath"
  }

  if ($AutoSetup -or -not (Test-Path -LiteralPath $VenvPython) -or -not (Test-Path -LiteralPath $VenvActivate)) {
    if (-not (Test-Path -LiteralPath $SetupScript)) {
      throw "Setup script not found at $SetupScript"
    }
    Write-Output "Running setup to ensure dependencies are installed..."
    & $SetupScript
  }

  if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "python.exe not found at $VenvPython"
  }

  Set-Location -LiteralPath $ProjectRoot
  New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
  Remove-Item -LiteralPath $StdOutPath, $StdErrPath -Force -ErrorAction SilentlyContinue

  $process = Start-Process -FilePath $VenvPython -ArgumentList @("-u", ('"' + $AppPath + '"')) -WorkingDirectory $ProjectRoot -PassThru -RedirectStandardOutput $StdOutPath -RedirectStandardError $StdErrPath

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
