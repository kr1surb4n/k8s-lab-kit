"""Chunker tests: offsets, overlap, and page mapping."""
import unittest

from app.chunker import chunk_text, page_for_offset


class ChunkerTests(unittest.TestCase):
    def test_offsets_match_text(self):
        text = " ".join(f"word{i}" for i in range(1000))
        chunks = chunk_text(text, max_words=100, overlap_words=10)
        self.assertGreater(len(chunks), 5)
        for chunk in chunks:
            self.assertEqual(chunk.text, text[chunk.start : chunk.end])
            self.assertLessEqual(len(chunk.text.split()), 100)

    def test_overlap_repeats_words(self):
        text = " ".join(f"w{i}" for i in range(250))
        chunks = chunk_text(text, max_words=100, overlap_words=20)
        first_tail = chunks[0].text.split()[-20:]
        second_head = chunks[1].text.split()[:20]
        self.assertEqual(first_tail, second_head)

    def test_last_chunk_is_not_duplicated_at_end(self):
        text = " ".join(f"w{i}" for i in range(120))
        chunks = chunk_text(text, max_words=100, overlap_words=10)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[-1].text.split()[-1], "w119")

    def test_page_map(self):
        first_page = " ".join(f"a{i}" for i in range(20))
        second_page = " ".join(f"b{i}" for i in range(20))
        text = first_page + "\n" + second_page
        second = text.index("b0")
        page_map = [(0, 1), (second, 2)]
        self.assertEqual(page_for_offset(page_map, 0), 1)
        self.assertEqual(page_for_offset(page_map, second), 2)
        self.assertEqual(page_for_offset(page_map, len(text) - 1), 2)
        chunks = chunk_text(text, max_words=20, overlap_words=0, page_map=page_map)
        self.assertEqual(chunks[0].page_start, 1)
        self.assertEqual(chunks[1].page_start, 2)

    def test_empty_text(self):
        self.assertEqual(chunk_text("   \n\t "), [])

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            chunk_text("one two", max_words=10)
        with self.assertRaises(ValueError):
            chunk_text("one two", max_words=20, overlap_words=20)


if __name__ == "__main__":
    unittest.main()
