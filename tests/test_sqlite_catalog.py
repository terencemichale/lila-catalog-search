import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.sqlite_catalog import initialize_database, search_database, haystack


class SQLiteCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "products.json"
        self.db = self.root / "products.sqlite3"
        self.products = [
            {"folder": "Cotton Shirt", "price": "RM50", "material": "Cotton", "care": "Hand wash"},
            {"folder": "Silk Wrap", "price": "RM80", "material": "Silk", "care": "Dry clean"},
            {"folder": "Cotton Wrap", "price": "RM70", "material": "Cotton", "care": "Hand wash"},
        ]
        self.source.write_text(json.dumps(self.products), encoding="utf-8")
        initialize_database(self.db, self.source)

    def test_indexed_substring_search_matches_expected_order(self):
        self.assertEqual([p["folder"] for p in search_database(self.db, "cotton", 10)],
                         ["Cotton Shirt", "Cotton Wrap"])

    def test_short_query_fallback(self):
        self.assertEqual(len(search_database(self.db, "RM", 10)), 3)

    def test_like_wildcards_are_literal(self):
        self.assertEqual(search_database(self.db, "%", 10), [])
        self.assertEqual(search_database(self.db, "_", 10), [])

    def test_limit(self):
        self.assertEqual(len(search_database(self.db, "cotton", 1)), 1)

    def test_reimport_replaces_snapshot(self):
        self.source.write_text(json.dumps(self.products[:1]), encoding="utf-8")
        initialize_database(self.db, self.source)
        self.assertEqual(len(search_database(self.db, "cotton", 10)), 1)

    def test_bad_import_does_not_replace_existing_catalog(self):
        self.source.write_text('{"not": "a list"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            initialize_database(self.db, self.source)
        self.assertEqual(len(search_database(self.db, "cotton", 10)), 2)

    def test_index_exists(self):
        with sqlite3.connect(self.db) as db:
            row = db.execute("SELECT name FROM sqlite_master WHERE name='product_search'").fetchone()
            self.assertIsNotNone(row)


if __name__ == "__main__":
    unittest.main()
