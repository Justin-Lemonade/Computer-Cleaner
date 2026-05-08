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
  $VenvPythonW = Join-Path $VenvDir "Scripts\pythonw.exe"
  $AppPath = Join-Path $ProjectRoot "App.py"
  $SetupScript = Join-Path $ProjectRoot "scripts\Setup.ps1"
  $RequirementsPath = Resolve-FirstExistingPath -Candidates @(
    (Join-Path $ProjectRoot "requirements.txt"),
    (Join-Path $ProjectRoot "Requirements.txt")
  ) -Description "requirements file"

  Write-Output "Current directory: $(Get-Location)"
  Write-Output "Project root: $ProjectRoot"
  Write-Output "Setup script: $SetupScript"
  Write-Output "Pythonw: $VenvPythonW"
  Write-Output "App: $AppPath"
  Write-Output "Requirements: $RequirementsPath"

  if (-not (Test-Path -LiteralPath $AppPath)) {
    throw "App.py not found at $AppPath"
  }

  if ($AutoSetup -or -not (Test-Path -LiteralPath $VenvPythonW) -or -not (Test-Path -LiteralPath $VenvActivate)) {
    if (-not (Test-Path -LiteralPath $SetupScript)) {
      throw "Setup script not found at $SetupScript"
    }
    Write-Output "Running setup to ensure dependencies are installed..."
    & $SetupScript
  }

  if (-not (Test-Path -LiteralPath $VenvPythonW)) {
    throw "pythonw.exe not found at $VenvPythonW"
  }

  Set-Location -LiteralPath $ProjectRoot

  $PythonPathEntries = @(
    $ProjectRoot,
    (Join-Path $ProjectRoot "src"),
    (Join-Path $ProjectRoot "src\data"),
    (Join-Path $ProjectRoot "src\core")
  )
  $ExistingPythonPath = [Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
  $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($ExistingPythonPath)) {
    $PythonPathEntries -join [IO.Path]::PathSeparator
  }
  else {
    (($PythonPathEntries + $ExistingPythonPath) -join [IO.Path]::PathSeparator)
  }

  $process = Start-Process -FilePath $VenvPythonW -ArgumentList @('"' + $AppPath + '"') -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Hidden

  Start-Sleep -Seconds 2
  if ($process.HasExited) {
    throw "UI exited immediately with code $($process.ExitCode)."
  }

  Write-Output "UI launched successfully. PID: $($process.Id)"
}
catch {
  Write-Output ""
  Write-Error "UI launcher failed: $($_.Exception.Message)"
  throw
}
