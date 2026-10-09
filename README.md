# LILA Catalog Search

**A Python API that turns a fabric catalog into a searchable, message-style experience.**

Search by product name, material, price, length, or care instructions. This portfolio edition extracts the working catalog-search portion of my LILA Fabrics project and runs with six fictional products. It needs no database, shop account, or API key.

## See it work

```json
{"query":"cotton","count":3,"results":[
  {"name":"Cotton Kurti Blue","price":"RM75","thumbnail":null,"ig_url":null},
  {"name":"Cotton Saree Indigo","price":"RM95","thumbnail":null,"ig_url":null},
  {"name":"Cotton Salwar Green","price":"RM85","thumbnail":null,"ig_url":null}
]}
```

Search for `cotton` to find three products, `silk` for two, or `Hand wash` for care-based matches. Unmatched queries return an empty result list; invalid limits and blank queries return explicit errors.

## Run locally

Requires Python 3.12. From a terminal:

```bash
git clone https://github.com/terencemichale/lila-catalog-search.git
cd lila-catalog-search
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` in PowerShell or `source .venv/bin/activate` on macOS/Linux. Then:

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8010
```

Open [the catalog](http://127.0.0.1:8010) or [interactive API documentation](http://127.0.0.1:8010/docs).

## API

| Endpoint | Behavior |
| --- | --- |
| `GET /` or `/tester` | Browser search interface |
| `POST /api/search` | JSON search, e.g. `{"query":"cotton","limit":3}` |
| `GET /api/health` | Service status and sample product count |
| `POST /api/whatsapp/webhook` | Local form-to-TwiML adapter demonstration |

The webhook demonstrates formatting only. It does not send messages and has no provider signature verification. Keep this demo on localhost; real deployment requires authentication, signature verification, rate limiting, and an operational review.

## Design decisions

- One search function supports both the JSON endpoint and the message adapter.
- A small JSON catalog keeps setup reproducible. A file timestamp/size cache reloads changed data.
- Pydantic validates request shape and limits; blank queries are rejected separately.
- Text is inserted into the browser using `textContent`, and XML responses escape special characters.
- The caption parser runs explicitly rather than writing the catalog on import.

## Verify

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests cover structured-field search, case handling, limits, cache invalidation, caption parsing, HTTP validation, and adapter output. CI runs these checks on Python 3.12.

## SQLite persistence and indexed search (optional)

The existing JSON backend remains the default. SQLite is an **opt-in, explicitly imported snapshot**, not a live synchronization service.

```bash
python -m scripts.init_sqlite
# macOS/Linux
LILA_SEARCH_BACKEND=sqlite python -m uvicorn backend.main:app --host 127.0.0.1 --port 8010
# PowerShell alternative
# $env:LILA_SEARCH_BACKEND="sqlite"; python -m uvicorn backend.main:app --host 127.0.0.1 --port 8010
```

The database uses SQLite FTS5 with a trigram index for literal substring searches of at least three characters. Short queries and SQL wildcard characters use a scan to preserve search semantics. Importing again replaces the snapshot transactionally. SQLite must be built with FTS5 trigram support; otherwise initialization fails rather than silently claiming indexed performance.

### Reproducible benchmark

```bash
python -m scripts.benchmark_search --rows 10000 --repeats 100
python -m pytest -q
```

The benchmark generates **synthetic** records, checks result parity, and reports median per-query latency for JSON scanning versus SQLite search. It includes both indexed and scan-fallback queries. Results vary by machine and workload; no speedup is claimed until measurements are recorded. See [architecture notes](docs/ARCHITECTURE.md).

## Architecture and reliability

Read [architecture and reliability notes](docs/ARCHITECTURE.md) for the request path, complexity, caching assumptions, failure modes, and a clearly labeled **not implemented** scaling design. Additional API boundary tests cover request limits, malformed inputs, and empty-result behavior.

## Scope and contribution

This is a curated edition of my existing application, with portfolio preparation assisted by AI. The original search logic, caption parsing, thumbnail naming, and browser tester are retained. Cleanup adds synthetic data, portable setup, import safety, documentation, and regression checks. The larger commerce platform, customer data, live integrations, and product photos are excluded.

See [provenance and limitations](docs/PROVENANCE.md). This repository does not claim a production deployment or business impact measurement.
