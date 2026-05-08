# Preview Support Expansion

Date: 2026-05-07

## Summary

Expanded the preview system beyond images, PDFs, DOCX, and plain text. The app now routes additional file families through dedicated preview builders while keeping unsupported, corrupt, or dependency-missing files from crashing queue generation.

## Added Preview Families

- Presentations: PPTX text extraction with `python-pptx`; PPT/PPTX/ODP visual thumbnail support when LibreOffice is installed.
- Spreadsheets: XLSX table/text preview with `openpyxl`; ODS table/text preview with `odfpy`; XLS visual fallback through LibreOffice.
- Office documents: DOCX remains supported; DOC/ODT/RTF use LibreOffice where available, with ODT/RTF text fallbacks.
- HTML/XML: readable text extraction with `beautifulsoup4`.
- Archives: ZIP/TAR/GZ via Python standard library; 7Z via `py7zr`; RAR via `rarfile`. Archives are listed only and never extracted.
- Email: EML via Python standard library; MSG via `extract-msg`.
- Text decoding: `chardet` is used for safer text and HTML decoding.

## Dependencies Added

Added to `requirements.txt`:

```text
python-pptx
openpyxl
odfpy
beautifulsoup4
extract-msg
py7zr
rarfile
chardet
```

## LibreOffice Support

LibreOffice is optional and is not required for app startup. When installed, the app detects `soffice.exe` from:

- `LIBREOFFICE_PATH`
- `SOFFICE_PATH`
- `C:\Program Files\LibreOffice\program\soffice.exe`
- `C:\Program Files (x86)\LibreOffice\program\soffice.exe`

LibreOffice is used in headless mode to convert supported Office/OpenDocument files to PDF. The existing PyMuPDF thumbnail path then renders the first page/slide/sheet as a PNG preview.

## Known Limitations

- PPT, DOC, and XLS need LibreOffice for reliable preview.
- PowerPoint visual thumbnails require LibreOffice; `python-pptx` only extracts text from PPTX files.
- Archive previews list contents only and do not extract files.
- RAR support may need external system support depending on the local `rarfile` setup.
- Audio/video previews remain out of scope for this pass.
- Missing optional dependencies return no preview instead of crashing.

## Testing Checklist

Regression formats:

- PNG
- JPG
- PDF
- DOCX
- TXT
- MD
- JSON
- CSV

New formats:

- PPTX
- PPT
- ODP
- XLSX
- XLS
- ODS
- DOC
- ODT
- RTF
- HTML
- XML
- ZIP
- 7Z
- RAR
- EML
- MSG

Failure scenarios:

- Corrupt Office files return no preview and do not crash.
- Missing LibreOffice does not break startup.
- Missing optional archive/email dependencies do not block sorting.
- Queue limit and background preview generation continue to work.
