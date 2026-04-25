# Dark Refactor Iteration - 2026-04-24

## What I was supposed to do (short)

- Refine the existing UI into a modern, minimal, ChatGPT-style dark interface.
- Keep preview as the dominant center element and move info to the left panel.
- Remove `UNSURE` from UI and action logic.
- Add a `RUN` execution behavior that relaunches immediately and auto-reloads on file changes.

## What I changed

1. `ui/MainWindow.py`
- Reworked layout into:
  - Left: `InfoPanel` metadata
  - Center: large preview stage (`FileCard`) with breathing space
  - Bottom: consistent action button row
- Replaced light styling with layered dark theme tokens:
  - `#0f0f0f`, `#171717`, `#212121`, `#2a2a2a`, `#2f2f2f`
  - Text colors `#ffffff`, `#b3b3b3`, `#6b6b6b`
  - Accent `#19c37d` only for primary/focus states
- Removed `UNSURE` button and `UNSURE` keyboard behavior.
- Mode selector now:
  - Shows only active mode by default
  - On hover, reveals `Training`, `Review`, `Sorting` in a horizontal slide
  - Uses subtle short animation and equal button sizes.
- Added `RUN` button behavior:
  - Pressing `RUN` enables run mode and relaunches immediately.
  - Uses `QFileSystemWatcher` to monitor UI files.
  - On source change, schedules automatic relaunch (no manual reload inside app).

2. `ui/FileCard.py`
- Refactored to preview-only component (no metadata duplication).
- Built a large, centered preview surface with icon + title.
- Kept design flat and minimal (no gradients, no decorative visuals).

3. `ui/InfoPanel.py`
- Refactored into a dedicated left metadata panel.
- Added compact rows for queue index, type, size, created, modified.
- Added a details section toggled by `MORE INFO`.

## Why these changes

- Matches the requested structural model: preview-first center, metadata separated left.
- Reduces visual noise and cognitive load by removing mixed content and excess color.
- Improves action consistency with equal-size buttons and predictable alignment.
- Implements a practical Python equivalent of `onChange -> rebuild -> relaunch -> show updated UI` via auto-relaunch.

## Validation notes

- Attempted syntax validation with `.\venv\Scripts\python.exe -m compileall ...`.
- Validation failed because this environment's Python launcher resolution is broken (`WindowsApps` access denied), so runtime verification was not possible here.
