# File Sorter AI (Desktop)

Desktop app for scanning, previewing, and labeling files so you can sort them the way you would — with optional ML suggestions later.

## Setup (Windows)

```powershell
cd file_sorter_ai
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r Requirements.txt
```

## Run (PySide6 desktop UI)

```powershell
python App.py
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
