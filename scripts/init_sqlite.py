"""Explicit one-time or repeatable import of JSON catalog into SQLite."""
import argparse
from pathlib import Path
from backend.sqlite_catalog import initialize_database
from paths import catalog_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=catalog_root() / "products.json")
    parser.add_argument("--database", type=Path, default=catalog_root() / "products.sqlite3")
    args = parser.parse_args()
    count = initialize_database(args.database, args.source)
    print(f"Imported {count} products into {args.database}")


if __name__ == "__main__":
    main()
