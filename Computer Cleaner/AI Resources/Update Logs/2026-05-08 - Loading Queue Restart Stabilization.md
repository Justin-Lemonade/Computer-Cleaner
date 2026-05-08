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
