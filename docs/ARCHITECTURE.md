# Architecture and Reliability Notes

## Scope

LILA Catalog Search is a **single-process, local portfolio application**, not a distributed production service. It uses six fictional catalog entries. This document describes the code as implemented and the trade-offs that would matter when extending it.

## Request path

```text
Browser tester  ---> POST /api/search ---> SearchRequest validation
                                            |
                                            v
                                      search_products()
                                            |
                                            v
                                  load_products() [Lock + cache]
                                            |
                                            v
                                    data/products.json
                                            |
                                            v
                                     JSON search result

Form webhook ---> POST /api/whatsapp/webhook ---> parse form
                                            |
                                            v
                                      search_products()
                                            |
                                            v
                                     escaped TwiML XML
```

The browser and form adapter reuse the same search function. The browser renders product text with `textContent` rather than interpreting catalog fields as HTML.

## Design choices and complexity

- **Storage:** a local JSON file keeps the demo reproducible and avoids credentials or infrastructure. There is no database, index, replication, or durable update API.
- **Search:** case-insensitive substring matching across product attributes. A full scan costs **O(N × L)** for N products and average searchable text length L; building a separate searchable string for every product also allocates temporary strings. This is appropriate for six products, not millions.
- **Result limit:** request validation accepts limits from 1 through 10. The search stops when the requested number of matches is found.
- **Cache:** an in-process cache uses file modification time and size as an invalidation stamp, protected by a threading lock. It avoids repeated JSON reads within a worker but is **not** a cross-process cache and is not transactional. Changes with identical timestamp and size may not be detected.
- **Availability:** the health endpoint reads the catalog, so missing or malformed data can affect it. There is no readiness/liveness distinction, durable metrics, tracing, or retry policy.
- **Security:** the webhook is a localhost-only formatting demonstration. It does **not** authenticate a provider request or implement rate limiting. Do not expose it publicly without those protections.

## Scaling design exercise (not implemented)

A larger catalog would require a separate durable data store and indexed search. A candidate design is:

1. Ingest and validate product records into a database.
2. Maintain an appropriate search index for product names and attributes.
3. Run stateless API instances behind a load balancer, with request limits and timeouts.
4. Add observability for latency percentiles, error rates, search misses, and index freshness.
5. Specify consistency behavior when a product update and index refresh occur at different times.
6. Load-test representative catalog sizes and query distributions before making throughput claims.

This is a **design discussion**, not a claim that the repository implements a distributed system.

## Failure modes to investigate next

| Failure | Current behavior | Candidate improvement |
| --- | --- | --- |
| Malformed products JSON | Request may fail | Validate at load time; explicit degraded readiness |
| Missing products file | Empty catalog | Surface missing-data status |
| Multi-worker deployment | Each worker caches independently | Externalize storage/cache or accept eventual consistency |
| Catalog changed during read | No snapshot guarantee | Atomic file replacement or database transaction |
| Public webhook requests | No signature verification | Verify provider signatures, apply rate limits |
| Larger catalog | Linear scan | Indexed query system |

## Interview discussion

Be ready to explain why a JSON file and linear scan were chosen for a small local demo, where the cache's invalidation assumptions break, and how you would design and measure a production replacement. Avoid presenting proposed scaling features as shipped.
