# 2026-05-08 - Loading Queue Restart Stabilization

## Summary

Stabilized loading and sorting flow in the desktop UI by moving blocking operations off the UI thread, adding timeout/recovery guards, and fixing restart process launching.

## Root Causes Found

1. Swipe confirmation path (`_submit_reason`) performed synchronous DB writes + file hashing on the UI thread.
2. Queue prefetch path executed metadata + preview generation synchronously on timer ticks in the UI thread.
3. Folder scan preloaded the full recursive file list up front (`list(iter_files(...))`), which delayed first render.
4. Restart path used `os.execl(...)` replacement; failures were not robustly recovered and detached relaunch was not guaranteed.
5. Animation code used `offset.x` instead of `offset.x()` for branch logic, which risked runtime errors during transition setup.

## Implemented Changes

### UI / Flow (`src/ui/MainWindow.py`)

- Added structured logging and timing instrumentation for decision, preview, and queue flow.
- Added background executor (`ThreadPoolExecutor`) for:
  - decision persistence (label + swipe write + hash),
  - preview batch generation.
- Added decision watchdog timeout (`20s`) and recovery:
  - if persistence stalls, UI recovers and proceeds instead of freezing indefinitely.
- Added polling timer for decision futures and explicit completion handler.
- Added on-demand queue refill when queue empties (works even with auto-prefetch disabled).
- Converted prefetch from sync main-thread work to async background batches, with safe UI-thread apply.
- Changed folder scan to incremental source iterator (`iter_files(...)`) with fast initial warm batch instead of loading full file list at once.
- Added restart via detached process launch (`QProcess.startDetached(...)`) then close current process.
- Added lifecycle cleanup:
  - stop timers,
  - cancel pending futures,
  - shut down executor on close/reset.
- Added large-file protections:
  - preview generation skip above `200MB`,
  - partial file hashing capped at `64MB`.
- Added animation failure recovery and fixed `QPoint` coordinate access (`offset.x()` / `offset.y()` usage path).

### Scanner (`src/core/scanner/Metadata.py`)

- Optimized MIME detection:
  - prefer `mimetypes.guess_type(...)` first,
  - only try `python-magic` fallback when needed,
  - skip magic fallback for very large files (`>64MB`).

### Preview (`src/core/preview/PreviewManager.py`)

- Added preview timing logs per file with success/failure markers.

### Database Connection Tuning

- `src/data/database/Db.py`
- `backend/db/connection.py`

Changes:
- set sqlite `timeout=3.0`,
- `PRAGMA journal_mode=WAL`,
- `PRAGMA busy_timeout=3000`.

### Logging (`src/utils/LoggingUtils.py`)

- Added millisecond timestamps.
- Enabled `force=True` to ensure app logging config applies consistently.

## Validation Run Notes

- `py_compile` passed for all touched modules.
- Offscreen UI smoke test passed:
  - MainWindow initialized,
  - scan -> keep -> reason flow completed,
  - no stuck pending decision state after action.

## Known Remaining Risk

- A third-party parsing call that blocks indefinitely inside a worker thread can still keep that worker occupied until completion; UI now remains responsive, but that worker cannot be force-killed safely from `ThreadPoolExecutor`.

## Option 6 Duplicate-Prevention Hardening (Hybrid Metadata + Hash Identity)

Additional pass completed to enforce "never re-sort already sorted files":

- Added `find_file_by_path_signature(...)` for fast metadata-first checks (`path + modified_date + size`) before hashing.
- Updated queue admission in `MainWindow`:
  - path-signature hit + `already_sorted=1` => skip immediately
  - hash lookup only when signature is uncertain/missing
  - hash match with sorted row => skip (supports moved/copied files)
  - preview reuse now validates file existence on disk before using cached path
  - if cached preview is missing, preview regenerates and DB is refreshed
- Added in-memory queue dedupe sets:
  - `_queued_paths` and `_queued_hashes`
  - prevents duplicate queue entries in the same session/prefetch cycle
- Fixed persistence consistency bug:
  - `mark_file_sorted(...)` now only runs when swipe save succeeds
  - removed broken exception path that referenced an undefined variable
- Filtered startup queue load to unsorted files only:
  - `list_files(...)` now returns rows where `already_sorted = 0`
- Added BLAKE3-first hashing with SHA-256 fallback:
  - `compute_file_hash(...)` attempts `blake3` when available, falls back safely to SHA-256
  - requirement added: `blake3`

### Verification Notes (manual scripted checks)

- Re-scan same folder after sorting one file:
  - sorted file is skipped, unsorted file remains queueable.
- Copy a sorted file into a new folder:
  - copied file is skipped via hash match (`already_sorted`).

## 2026-05-09 UI Interaction Fixes

- Random folder picker updated from deterministic selection to true random selection across available common folders, with rotation away from the currently active source when possible.
- Folder selection now supports queue merge modes:
  - `Replace Queue`
  - `Add To Start`
  - `Add To End`
- Queue session limit support added so manual merges can extend queue length beyond base settings limit for the current load session.
- `Add To Start` behavior now prioritizes newly loaded files before existing queued files.
- Action buttons updated with stronger hover treatment:
  - larger hover size
  - stronger multidirectional glow/shadow
  - increased spacing between buttons to avoid overlap.
- Mode selector vertical alignment adjusted to center-align with bottom action controls.
- Mode selector now has subtle hover glow on container.
- Swipe transition timing adjusted for smoother staging and clearer reveal:
  - longer outgoing and incoming motion
  - delayed incoming rise for better separation.
- More-info flow updated to enable an enlarged preview mode signal:
  - details toggle now switches FileCard focus mode for bigger rendered preview content.
