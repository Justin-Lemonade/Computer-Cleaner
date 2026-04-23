from __future__ import annotations

from pathlib import Path

import streamlit as st

from database.Db import init_db, list_files
from scanner.ScanFiles import scan_and_store


def main() -> None:
    st.set_page_config(page_title="File Sorter AI", layout="wide")
    init_db()

    st.title("File Sorter AI (Prototype)")

    folder = st.text_input("Folder to scan", value=str(Path.home() / "Downloads"))
    if st.button("Scan"):
        scan_and_store(Path(folder))
        st.success("Scan complete.")

    st.subheader("Files")
    rows = list_files(limit=50)
    if not rows:
        st.info("No files yet. Click Scan.")
        return

    for row in rows:
        st.write(f"**{row['filename']}** — {row['path']}")


if __name__ == "__main__":
    main()
