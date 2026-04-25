# Install Attempt - 2026-04-24

## What I was supposed to do (short)

- Explain why packages were not installed yet.
- Attempt to install required packages as best as possible.

## What happened (why nothing was installed automatically)

- This Codex environment does not have `python`, `py`, `pip`, `winget`, or `choco` available on PATH.
- Without a Python interpreter + pip, there is no way to install the dependencies in `requirements.txt`.
- Network access is also restricted here, so even downloading a Python installer from the internet is not reliable/possible from inside this session.

## What I did instead (best effort inside constraints)

- Added automation scripts so installation becomes a one-command step as soon as Python is available:
  - `scripts/Setup.ps1` creates `venv`, upgrades pip, installs `requirements.txt`
  - `scripts/Run.ps1` activates `venv` and runs `App.py`
- Updated `README.md` to use these scripts.

## What you should do on your machine

1. Install Python 3.x (and ensure `python` works in PowerShell).
2. Run `.\scripts\Setup.ps1`
3. Run `.\scripts\Run.ps1`

