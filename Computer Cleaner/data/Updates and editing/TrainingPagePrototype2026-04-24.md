# Training Page Prototype - 2026-04-24

## What I was supposed to do (short)

- Build only the first page UI in PySide6 (Training page), close to your design vision.
- Keep other pages non-functional for now.
- Use existing files and add structure as needed.

## What I changed

1. Rebuilt the main UI page as a dedicated Training-mode prototype.
- File updated: `ui/MainWindow.py`
- Added:
  - Top bar with large Training title and a top-right menu (`Settings`, `History`, `Search`).
  - Center stage with one interactive file card at a time.
  - Bottom curved action dock with `DELETE`, `ARCHIVE`, `UNSURE`, `SAVE`, `MORE INFO`, `OPEN FILE`.
  - Bottom-right hover-expand mode panel (`Training`, `Testing`, `Automation`) with active highlight.

2. Added card decision animations to mimic swipe/browse behavior.
- File updated: `ui/MainWindow.py`
- Added per-action motion:
  - `DELETE` -> card moves left.
  - `SAVE` -> card moves right.
  - `ARCHIVE` -> card moves up.
  - `UNSURE` -> card moves down.
- Added fade + slide transition between cards.

3. Wired keyboard controls for fast training flow.
- File updated: `ui/MainWindow.py`
- Shortcuts:
  - Left/A = Delete
  - Right/D = Save
  - Up/W = Archive
  - Down/S = Unsure
  - Space = toggle detail view

4. Upgraded the card UI to match your metadata bubble concept.
- File updated: `ui/FileCard.py`
- Added:
  - Large filename header.
  - Path line.
  - Rounded metadata bubbles (Created, Last Edited, File Type, File Size).
  - Expandable detail block for more information.
  - Inline key-hint row.

5. Connected decisions to logging behavior for training where IDs exist.
- File updated: `ui/MainWindow.py`
- Behavior:
  - If current card has a real database `id`, action writes a label event via `save_label(...)`.
  - If there are no scanned files yet, prototype falls back to mock cards for UI flow testing.

## Why these changes

- You asked for first-page-only UI with a Tinder-like one-card decision flow.
- The design preserves speed and low cognitive load:
  - One prominent card.
  - Fixed decision controls.
  - Keyboard mirror bindings.
- The mode panel and menu are included as scaffolding so expansion to Testing/Automation does not require a UI rewrite.

## Notes

- This is intentionally a UI prototype slice, not full app behavior.
- `Testing` and `Automation` modes are visual-only placeholders in this build.
- I could not run Python runtime checks in this environment because `python`/`py` are unavailable on PATH here.

