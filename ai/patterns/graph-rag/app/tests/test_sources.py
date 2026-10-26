"""Source loader tests: HTML stripping, file filters, and the lab corpus."""
import tempfile
import unittest
from pathlib import Path

from app.sources import (
    content_hash,
    html_to_text,
    is_included,
    load_lab_corpus,
    normalize_text,
    paper_title,
)

LAB = Path(__file__).resolve().parents[2] / "corpus"


class SourceTests(unittest.TestCase):
    def test_html_strips_scripts_and_styles(self):
        raw = "<h1>Hello</h1><script>bad()</script><style>x{}</style><p>World &amp; more</p>"
        text = normalize_text(html_to_text(raw))
        self.assertIn("Hello", text)
        self.assertIn("World & more", text)
        self.assertNotIn("bad()", text)
        self.assertNotIn("x{}", text)

    def test_normalize_collapses_blank_lines(self):
        self.assertEqual(normalize_text("a\r\n\n\n\nb  c"), "a\n\nb c")

    def test_normalize_removes_nul_bytes(self):
        self.assertEqual(normalize_text("a\x00b"), "ab")

    def test_include_and_exclude(self):
        include = ["**/*.md", "**/*.txt"]
        exclude = ["My Games/**", "zip/**"]
        self.assertTrue(is_included("md/note.md", include, exclude))
        self.assertTrue(is_included("note.md", include, exclude))
        self.assertTrue(is_included("txt/deep/note.txt", include, exclude))
        self.assertFalse(is_included("My Games/save.txt", include, exclude))
        self.assertFalse(is_included("zip/archive.txt", include, exclude))
        self.assertFalse(is_included("image.png", include, exclude))

    def test_content_hash_changes_with_metadata(self):
        first = content_hash("text", {"tags": ["a"]})
        second = content_hash("text", {"tags": ["b"]})
        self.assertNotEqual(first, second)
        self.assertEqual(first, content_hash("text", {"tags": ["a"]}))

    def test_paper_title_is_readable(self):
        self.assertEqual(
            paper_title("250100004_news_homepages_layouts.pdf"),
            "250100004 news homepages layouts",
        )

    def test_lab_corpus_parses_front_matter(self):
        docs = list(load_lab_corpus(LAB, limit=1))
        self.assertEqual(len(docs), 1)
        document = docs[0]
        self.assertEqual(document.id, "doc-01")
        self.assertEqual(document.corpus, "lab")
        self.assertTrue(document.title)
        self.assertTrue(document.section)
        self.assertIsInstance(document.source, dict)
        self.assertNotIn("---", document.text[:10])

    def test_missing_pdf_dependency_is_a_clear_error(self):
        # A missing file is the common case; it must raise OSError, not crash.
        from app.sources import read_pdf

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(OSError):
                read_pdf(Path(tmp) / "missing.pdf")


if __name__ == "__main__":
    unittest.main()
