# Cleanup Structure Notes

## What a Cleanup Branch Does

A cleanup branch is a separate Git branch used for organizing files without changing the main working branch directly. It lets us move folders, rename files, and review the result before merging those changes back into the main project history.

For this pass, the branch is named `cleanup-structure`. The requested `codex/cleanup-structure` name could not be created in this repository, so the simpler branch name was used.

## Why Layers Matter

Layered project structure keeps each kind of code in a predictable place. That makes the project easier for people and AI assistants to navigate, safer to refactor, and less likely to grow into one large mixed folder.

## Layer Meanings

`main.py` is the entry point. It should only start the app and delegate work elsewhere.

`config/` stores settings, constants, and environment-driven configuration.

`src/ui/` stores GUI and frontend code. This layer can depend on core logic, but core logic should not depend on UI code.

`src/ui/components/` stores reusable UI pieces that can be shared across screens.

`src/core/` stores business logic: scanning rules, preview decisions, labeling behavior, ML helpers, and other app behavior that should work without a GUI.

`src/data/` stores persistence code, database models, file I/O, and data access.

`src/utils/` stores small shared helper functions used by multiple layers.

`assets/` stores non-code visual or font resources, split by type.

`docs/` stores project documentation.

`AI Resources/` stores AI-facing material such as installed skills, setup notes, and update logs.

## This Pass

This pass only moved and created files and folders. It did not update imports, launch scripts, or tests.
