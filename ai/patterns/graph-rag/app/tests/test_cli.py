"""CLI guard tests: private corpora may not enter the eval database."""
import unittest

from app.cli import guard_corpus_db
from app.config import load_settings


class CliGuardTests(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings()

    def test_notes_with_eval_name_is_rejected(self):
        with self.assertRaises(SystemExit):
            guard_corpus_db(
                "notes", "eval", self.settings.dsn("eval"), self.settings
            )

    def test_notes_with_explicit_eval_dsn_is_rejected(self):
        with self.assertRaises(SystemExit):
            guard_corpus_db(
                "papers", "custom", self.settings.dsn("eval"), self.settings
            )

    def test_notes_with_private_dsn_is_allowed(self):
        guard_corpus_db(
            "notes", "private", self.settings.dsn("private"), self.settings
        )

    def test_lab_with_private_dsn_is_rejected(self):
        with self.assertRaises(SystemExit):
            guard_corpus_db(
                "lab", "private", self.settings.dsn("private"), self.settings
            )


if __name__ == "__main__":
    unittest.main()
