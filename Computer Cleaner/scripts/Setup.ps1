param(
  [switch]$Quiet
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

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvDir = Join-Path $ProjectRoot "venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$RequirementsPath = Resolve-FirstExistingPath -Candidates @(
  (Join-Path $ProjectRoot "requirements.txt"),
  (Join-Path $ProjectRoot "Requirements.txt")
) -Description "requirements file"
$StampPath = Join-Path $VenvDir ".requirements.stamp"
$PythonInstallRoot = Join-Path $ProjectRoot ".python"
$PythonDownloadCache = Join-Path $ProjectRoot ".uv-cache"

function Get-LocalPythonExe {
  if (-not (Test-Path -LiteralPath $PythonInstallRoot)) {
    return $null
  }

  $candidate = Get-ChildItem -LiteralPath $PythonInstallRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "cpython-*-windows-x86_64-none" } |
    ForEach-Object { Join-Path $_.FullName "python.exe" } |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1

  return $candidate
}

function Ensure-LocalPython {
  $pythonExe = Get-LocalPythonExe
  if ($pythonExe) {
    return $pythonExe
  }

  $uv = Get-Command uv -ErrorAction SilentlyContinue
  if (-not $uv) {
    throw "No local Python runtime was found under .python and uv.exe is not available to install one."
  }

  New-Item -ItemType Directory -Force -Path $PythonInstallRoot | Out-Null
  New-Item -ItemType Directory -Force -Path $PythonDownloadCache | Out-Null
  & $uv.Source python install 3.13 --install-dir $PythonInstallRoot --cache-dir $PythonDownloadCache --no-registry

  $pythonExe = Get-LocalPythonExe
  if (-not $pythonExe) {
    throw "uv installed Python, but python.exe was not found under $PythonInstallRoot."
  }

  return $pythonExe
}

function Get-FileStamp([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    return $null
  }
  return (Get-Item -LiteralPath $Path).LastWriteTimeUtc.Ticks
}

$requirementsStamp = Get-FileStamp $RequirementsPath
$cachedStamp = Get-FileStamp $StampPath
$needsSetup = -not (Test-Path -LiteralPath $VenvPython) -or -not $cachedStamp -or $cachedStamp -ne $requirementsStamp

if (-not $needsSetup) {
  if (-not $Quiet) {
    Write-Host "Setup already current."
  }
  return
}

if (-not (Test-Path -LiteralPath $VenvDir)) {
  $pythonExe = Ensure-LocalPython
  & $pythonExe -m venv $VenvDir
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
  throw "Virtual environment creation failed."
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r $RequirementsPath

[System.IO.Directory]::CreateDirectory($VenvDir) | Out-Null
[System.IO.File]::WriteAllText($StampPath, [string]$requirementsStamp)

if (-not $Quiet) {
  Write-Host "Setup complete."
}
