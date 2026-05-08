# Launcher Fix Report

## What I changed
- Rebuilt the project venv with a local Python runtime so `venv\Scripts\python.exe` no longer points at the Windows Store alias.
- Updated `scripts\Run.ps1` to print debug paths, activate the venv, start the app as a detached process, and fail loudly if the app exits immediately.
- Updated `scripts\Setup.ps1` so future repairs prefer the local `.python` runtime and only install Python through `uv` when it is missing.

## Why I changed it
- The launcher was failing because the original venv resolved to a blocked Windows Store Python path.
- The app needed a launch path that survives spaces in `Computer Cleaner` and keeps running instead of closing instantly.
- Setup needed a reliable fallback for machines where system Python is not on PATH.

## Evaluation
- The launcher now resolves the real project root, uses the working venv, and successfully starts the desktop app process.
- The remaining output warning is non-fatal, but the core failure mode is fixed and the app stays running after launch.
