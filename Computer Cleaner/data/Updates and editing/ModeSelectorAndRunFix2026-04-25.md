# Mode Selector + Run Clarification - 2026-04-25

## What I was supposed to do (short)

- Fix mode-selector lag/motion behavior.
- Remove in-app RUN button.
- Update keybindings (Down/S -> More Info, Space -> Open File).
- Keep preview dominant and improve responsiveness.
- Keep dark minimal design language consistent.

## What I changed

1. `ui/MainWindow.py`
- Replaced mode selector implementation with stacked-button animation:
  - Default: only active mode visible.
  - Hover: three modes expand left from stacked state.
  - Unselected buttons fade in on expand and fade to black (opacity 0) on collapse.
  - Selection collapse is immediate and puts selected mode back in primary slot.
- Removed in-app RUN button and all auto-restart watcher logic from UI.
- Kept dropdown `Menu` button but removed menu indicator arrow rendering to fix right-edge arrow misalignment.
- Updated keyboard mapping:
  - `A/Left` -> Not Needed
  - `D/Right` -> Keep
  - `W/Up` -> Archive
  - `S/Down` -> More Info
  - `Space` -> Open File
- Improved transition motion for file cards to feel directional and weighted:
  - Accelerated exit with weight-drop keyframe.
  - Incoming card overshoots then settles.
- Switched body to splitter-based responsive layout so left info and center preview adapt better to different sizes.

2. `ui/FileCard.py`
- Removed icon rendering entirely (no emoji, no uncertain icon palette).
- Kept preview as a clean, dominant center surface with text-only focus.

3. `ui/InfoPanel.py`
- Updated shortcut hint text to match new keybind behavior.

## Why these changes

- The new mode selector avoids layout jitter and matches the requested stacked-then-expand interaction.
- Removing in-app RUN avoids confusion with Codex’s external run configuration.
- Keybind changes align behavior with your specified controls.
- Responsive splitter layout improves behavior on smaller/larger window sizes while keeping preview primary.

## Validation notes

- Runtime launch validation is still blocked in this environment due Python interpreter issues.
- Structural checks were done by scanning updated modules for removed `UNSURE` and removed in-app RUN logic.
