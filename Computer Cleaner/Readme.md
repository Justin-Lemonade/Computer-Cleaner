# File Sorter AI (Desktop)

Desktop app for scanning, previewing, and labeling files so you can sort them the way you would — with optional ML suggestions later.

## Setup (Windows)

```powershell
cd "C:\Users\I'm not a hacker\OneDrive\Documents\New project"
.\scripts\Setup.ps1
```

## Run (PySide6 desktop UI)

```powershell
.\scripts\Run.ps1
```

## Optional: Streamlit prototype UI

```powershell
streamlit run AppStreamlit.py
```

## Data folders

Runtime data is stored under `data/`:

- `data/previews/` generated previews (PDF renders, extracted text, etc.)
- `data/thumbnails/` generated thumbnails
- `data/logs/` log files


## Install Claude/Codex skills (repo-managed)

After cloning, install project-managed skills into local Claude/Codex skill folders:

```bash
cd "Computer Cleaner"
bash scripts/install_skills.sh            # symlink mode (default)
bash scripts/install_skills.sh copy       # copy mode
```

Installed skill set includes:
- TDD Guard
- Context Engineering Kit
- Claude Scientific Skills
- Claude Mem
- Existing non-excluded project skills from `AI Resources/Skills/`

Excluded from this repo-managed pack: SEO, marketing, code security, humanizer.
