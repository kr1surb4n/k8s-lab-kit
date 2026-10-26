# Example: OCR for image-only PDFs

Many papers are scans. PyMuPDF extracts no text from those pages, so they are
skipped or indexed only by title and summary. This example renders **only the
low-text pages** and runs the installed `tesseract` command-line tool on them.
No Python OCR package is added.

OCR is opt-in per source or per ingest run.

## Requirements

```bash
command -v tesseract
tesseract --list-langs
```

The current host has `eng`, `pol`, and `osd` language data. A missing
`tesseract` is not fatal: the loader warns and keeps the native PDF text, and
the result is not cached under the OCR key.

## Run it on the private corpora

```bash
cd ai/patterns/graph-rag

# One trial document first; OCR only the pages with too little text.
.venv/bin/python -m app.cli ingest papers --limit 1 --ocr --force

# Full paper library. This can be slow: each scanned page is rendered and OCRed.
.venv/bin/python -m app.cli ingest papers --ocr --force

# Notes can contain scanned PDFs too.
.venv/bin/python -m app.cli ingest notes --ocr
```

`--ocr` is a per-run override. To make it the default for a source, edit the
private config (never commit it):

```yaml
sources:
  papers:
    # ...
    ocr: true
    ocr_lang: eng        # or "eng+pol" for mixed English/Polish scans
    ocr_min_words: 10    # pages below this word count are OCRed
    ocr_dpi: 200         # higher is slower and larger
```

The same four fields exist under `sources.notes`.

## Verify the PDF reader without private data

This creates a one-page PDF containing only an image of text:

```bash
.venv/bin/python - <<'PY'
import tempfile
from pathlib import Path
import pymupdf
from app.sources import read_pdf

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    source = pymupdf.open()
    page = source.new_page(width=700, height=220)
    page.insert_text((45, 120), "Kubernetes image-only PDF test", fontsize=30)
    png = tmp / "page.png"
    page.get_pixmap(dpi=200).save(png)
    source.close()

    document = pymupdf.open()
    target = document.new_page(width=700, height=220)
    target.insert_image(target.rect, filename=str(png))
    pdf = tmp / "image-only.pdf"
    document.save(pdf)
    document.close()

    native, _ = read_pdf(pdf)
    recognized, page_map = read_pdf(pdf, ocr=True, ocr_min_words=1)
    print("native:", repr(native))
    print("ocr:", repr(recognized), page_map)
PY
```

Expected output:

```text
native: ''
ocr: 'Kubernetes image-only PDF test' [(0, 1)]
```

The automated version is:

```bash
.venv/bin/python -m unittest app.tests.test_ocr -v
```

## What changed

- `read_pdf()` accepts `ocr`, `ocr_lang`, `ocr_min_words`, and `ocr_dpi`.
- A page is OCRed only when native text has fewer than `ocr_min_words` words.
- OCR text is used only when it contains more words than the native text.
- OCR cache entries include the OCR settings, so enabling OCR does not reuse the
  old native-text cache.
- `--ocr` overrides a source's setting for one ingestion run.
- `SourceDocument.page_map` continues to point citations at the real page.

## Caching and cost

The existing cache under `~/.cache/graphrag/pdf-text/` is keyed by path, size,
mtime, and OCR settings. A native extraction and an OCR extraction are separate
entries. Re-indexing an unchanged scanned PDF reuses the OCR result; changing
`ocr_lang`, `ocr_min_words`, or `ocr_dpi` produces a new entry and re-runs OCR.

OCR is CPU work. Start with `--limit 1` and one source, inspect the indexed
chunks, then run the full corpus. A 200 DPI page is usually a good compromise;
300 DPI helps small print but is noticeably slower.

## Limitations

- OCR quality depends on scan quality and language data. Rotated pages, tables,
  and two-column layouts can come out in the wrong order.
- The loader does not detect page rotation or deskew. `tesseract` handles some
  rotation automatically, but not reliably.
- A page with a text layer and a bad scan is not OCRed unless its native word
  count is below the threshold. Lower `ocr_min_words` to OCR more pages.
- OCR text is still chunked and embedded like any other PDF text. It does not
  create a separate provenance type; the citation still points to the PDF page.
