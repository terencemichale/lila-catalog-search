"""Optional SQLite-backed catalog with FTS5 trigram indexing.

Explicitly initialize the database from JSON; no writes occur at import time.
FTS5 trigram supports indexed LIKE for queries of at least three characters.
Short queries use a normal SQLite scan to preserve substring semantics.
"""
import json
import sqlite3
from pathlib import Path


def haystack(product: dict) -> str:
    return " ".join(str(product.get(k, "")) for k in
                    ("folder", "price", "material", "length", "care")).lower()


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: Path, products_path: Path) -> int:
    """Replace the catalog atomically from a JSON snapshot."""
    products = json.loads(products_path.read_text(encoding="utf-8"))
    if not isinstance(products, list) or any(not isinstance(p, dict) for p in products):
        raise ValueError("Expected a JSON list of product objects")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY, payload TEXT NOT NULL, searchable TEXT NOT NULL
        )""")
        db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS product_search
            USING fts5(searchable, tokenize='trigram')""")
        db.execute("DELETE FROM product_search")
        db.execute("DELETE FROM products")
        rows = [(i + 1, json.dumps(p), haystack(p)) for i, p in enumerate(products)]
        db.executemany("INSERT INTO products(id, payload, searchable) VALUES (?, ?, ?)", rows)
        db.executemany("INSERT INTO product_search(rowid, searchable) VALUES (?, ?)",
                       [(id_, text) for id_, _, text in rows])
    return len(products)


def search_database(db_path: Path, query: str, limit: int = 3) -> list[dict]:
    needle = query.strip().lower()
    if not needle:
        return []
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    with connect(db_path) as db:
        # SQLite's trigram index can optimize LIKE only without an ESCAPE clause.
        # SQL wildcard characters use instr() for literal substring semantics.
        if len(needle) >= 3 and "%" not in needle and "_" not in needle:
            rows = db.execute("""
                SELECT p.payload FROM product_search AS s
                JOIN products AS p ON p.id = s.rowid
                WHERE s.searchable LIKE ?
                ORDER BY p.id LIMIT ?
            """, ("%" + needle + "%", limit)).fetchall()
        else:
            rows = db.execute("""
                SELECT payload FROM products
                WHERE instr(searchable, ?) > 0
                ORDER BY id LIMIT ?
            """, (needle, limit)).fetchall()
    return [json.loads(row["payload"]) for row in rows]
