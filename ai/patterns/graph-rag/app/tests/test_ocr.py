"""OCR tests using a tiny image-only PDF; no external model is needed."""
import shutil
import tempfile
import unittest
from pathlib import Path

from app.sources import iter_documents, read_pdf

try:
    import pymupdf
except ImportError:  # pragma: no cover - the venv installs it
    pymupdf = None

TESSERACT = shutil.which("tesseract")


# Make an image-only PDF with readable text and return its path.
def _image_only_pdf(directory: Path) -> Path:
    source = pymupdf.open()
    page = source.new_page(width=700, height=220)
    page.insert_text((45, 120), "Kubernetes image-only PDF test", fontsize=30)
    image = directory / "page.png"
    page.get_pixmap(dpi=200).save(image)
    source.close()

    document = pymupdf.open()
    target = document.new_page(width=700, height=220)
    target.insert_image(target.rect, filename=str(image))
    pdf = directory / "image-only.pdf"
    document.save(pdf)
    document.close()
    return pdf


@unittest.skipUnless(pymupdf and TESSERACT, "PyMuPDF and tesseract are required")
class OcrTests(unittest.TestCase):
    def test_native_text_is_empty_on_an_image_only_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _image_only_pdf(Path(tmp))
            text, page_map = read_pdf(pdf)
            self.assertEqual(text, "")
            self.assertEqual(page_map, [])

    def test_ocr_recovers_text_and_page_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _image_only_pdf(Path(tmp))
            text, page_map = read_pdf(pdf, ocr=True, ocr_min_words=1)
            self.assertIn("Kubernetes", text)
            self.assertIn("image-only", text)
            self.assertEqual(page_map, [(0, 1)])

    def test_ocr_uses_a_separate_cache_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _image_only_pdf(Path(tmp))
            native, _ = read_pdf(pdf)
            recognized, _ = read_pdf(pdf, ocr=True, ocr_min_words=1)
            second, _ = read_pdf(pdf, ocr=True, ocr_min_words=1)
            self.assertEqual(native, "")
            self.assertEqual(recognized, second)

    def test_source_loader_passes_ocr_override(self):
        from app.config import Settings, SourceConfig

        with tempfile.TemporaryDirectory() as tmp:
            _image_only_pdf(Path(tmp))
            source = SourceConfig(
                name="notes",
                kind="files",
                path=Path(tmp),
                include=["**/*.pdf"],
                min_words=2,
                ocr=True,
                ocr_min_words=1,
            )
            settings = Settings(sources={"notes": source})
            documents = list(iter_documents(settings, "notes"))
            self.assertEqual(len(documents), 1)
            self.assertIn("Kubernetes", documents[0].text)
            self.assertEqual(documents[0].page_map, [(0, 1)])


if __name__ == "__main__":
    unittest.main()
