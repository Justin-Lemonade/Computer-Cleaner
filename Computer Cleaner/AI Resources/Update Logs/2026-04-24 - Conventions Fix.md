# Conventions Fix — 2026-04-24

## What I was supposed to do (short)

- Change back `__init__.py` (and other conventional filenames) so the project follows normal Python conventions and avoids tooling/import problems.
- Keep “named” module files (like `Metadata.py`) in CamelCase as you requested.

## What I changed

- Renamed package initializer files:
  - `**/__Init__.py` → `**/__init__.py` (all packages: `database`, `scanner`, `preview`, `ui`, `logic`, `ml`, `utils`)
- Renamed common convention files:
  - `Requirements.txt` → `requirements.txt`
  - `Readme.md` → `README.md`
  - `.Gitkeep` → `.gitkeep` (in `data/` and subfolders)
- Updated `README.md` to reference `requirements.txt` and the correct folder name (`Computer Cleaner`).

## Why these changes

- `__init__.py` is a long-standing Python packaging convention. Many tools and workflows assume it exists with that exact spelling. Keeping it standard reduces “mystery import” issues.
- `requirements.txt` and `README.md` are de-facto standard names that tooling and humans expect.
- `.gitkeep` is conventionally lowercase; it’s not special to git, but teams often standardize on it.

## Notes / risks

- The project folder on disk is `Computer Cleaner/` (not `file_sorter_ai/`). I updated `README.md` to match the actual folder name to prevent setup confusion.

