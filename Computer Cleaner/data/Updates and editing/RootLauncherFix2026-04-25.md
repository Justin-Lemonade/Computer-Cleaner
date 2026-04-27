# Root Launcher Fix - 2026-04-25

## What I was supposed to do (short)

- Fix the launch commands so they work from the repository root.
- Stop reinstalling packages on every app launch.
- Explain why the earlier commands failed.

## What I changed

1. Added root-level launcher wrappers.
- Files added:
  - `scripts/Setup.ps1`
  - `scripts/Run.ps1`
- These wrappers forward to the project-local scripts inside `Computer Cleaner/`, so you can run from the root folder you were already using.

2. Made setup idempotent.
- File updated:
  - `Computer Cleaner/scripts/Setup.ps1`
- Behavior now:
  - Creates the virtual environment if missing.
  - Installs packages only when the requirements file changed or the venv is missing.
  - Skips reinstall when setup is already current.

3. Made run launch-only.
- File updated:
  - `Computer Cleaner/scripts/Run.ps1`
- Behavior now:
  - Launches the desktop app directly.
  - Does not reinstall packages during normal app startup.
  - Can trigger setup only if the venv is missing.

4. Updated the project README.
- File updated:
  - `Computer Cleaner/README.md`
- It now points to the root launcher commands instead of the project-local path, which matches how you were actually running the app.

## Why the earlier commands failed

- The path `.\scripts\Setup.ps1` did not exist at the repository root before this fix.
- The app entry file `App.py` also lives inside `Computer Cleaner/`, not the root folder.
- The combined command was trying to install and run from the wrong directory, so PowerShell could not find `requirements.txt` or `App.py`.

## Validation notes

- I could not fully run the desktop app from inside this sandbox because Python launcher resolution is still not reliable here.
- The command structure is now aligned with the actual repo layout, so it should work from your PowerShell session once Python is available on the machine.

