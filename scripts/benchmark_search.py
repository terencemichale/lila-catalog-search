"""Compare JSON full scans against SQLite indexed search using synthetic records.

Run: python -m scripts.benchmark_search --rows 1000 --repeats 100
Results are machine-dependent; report both absolute latency and workload.
"""
import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from backend.sqlite_catalog import haystack, initialize_database, search_database


def json_search(products: list[dict], query: str, limit: int) -> list[dict]:
    results = []
    for product in products:
        if query.lower() in haystack(product):
            results.append(product)
            if len(results) >= limit:
                break
    return results


def benchmark(fn, repeats: int) -> float:
    samples = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns() - start) / 1_000_000)
    return statistics.median(samples)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=10000)
    parser.add_argument("--repeats", type=int, default=100)
    args = parser.parse_args()
    if args.rows < 1 or args.repeats < 1:
        parser.error("rows and repeats must be positive")
    products = [
        {"folder": f"Fabric {i:06d}", "material": "Cotton" if i % 4 == 0 else "Silk",
         "price": f"RM{i % 300}", "length": "6m", "care": "Hand wash",
         "ig_url": None} for i in range(args.rows)
    ]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        json_path = root / "products.json"
        db_path = root / "products.sqlite3"
        json_path.write_text(json.dumps(products), encoding="utf-8")
        initialize_database(db_path, json_path)
        print(f"Rows: {args.rows}, repeats: {args.repeats}, units: median ms per search")
        for query in ("Cotton", "Fabric 009", "RM2", "nonexistent"):
            a = json_search(products, query, 10)
            b = search_database(db_path, query, 10)
            assert a == b, f"Search mismatch: {query}"
            json_ms = benchmark(lambda: json_search(products, query, 10), args.repeats)
            sqlite_ms = benchmark(lambda: search_database(db_path, query, 10), args.repeats)
            print(f"{query!r}: JSON {json_ms:.4f} ms | SQLite {sqlite_ms:.4f} ms | "
                  f"SQLite/JSON {sqlite_ms / json_ms:.2f}x")


if __name__ == "__main__":
    main()
