from threading import Lock

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
from pathlib import Path
from xml.sax.saxutils import escape
from pydantic import BaseModel, Field

from catalog_keys import thumbnail_filename_for_product
from paths import catalog_root

app = FastAPI(title="LILA Catalog Search", version="1.0.0")

CATALOG_DIR = catalog_root()
PRODUCTS_FILE = CATALOG_DIR / "products.json"
THUMBNAILS_DIR = CATALOG_DIR / "thumbnails"
_PRODUCTS_CACHE_LOCK = Lock()
_PRODUCTS_CACHE: dict[str, object] = {
    "stamp": None,
    "products": [],
}

if THUMBNAILS_DIR.exists():
    app.mount("/thumbnails", StaticFiles(directory=THUMBNAILS_DIR), name="thumbnails")


class SearchRequest(BaseModel):
    query: str = Field(max_length=200)
    limit: int = Field(default=3, ge=1, le=10)


def _products_file_stamp() -> tuple[int, int] | None:
    if not PRODUCTS_FILE.exists():
        return None
    stat = PRODUCTS_FILE.stat()
    return (stat.st_mtime_ns, stat.st_size)

def load_products():
    stamp = _products_file_stamp()
    with _PRODUCTS_CACHE_LOCK:
        if _PRODUCTS_CACHE["stamp"] == stamp:
            return list(_PRODUCTS_CACHE["products"])

        if stamp is None:
            products: list[dict] = []
        else:
            with open(PRODUCTS_FILE, encoding="utf-8") as f:
                products = json.load(f)

        _PRODUCTS_CACHE["stamp"] = stamp
        _PRODUCTS_CACHE["products"] = products
        return list(products)


def normalize_query(value: str) -> str:
    return value.strip()


def _build_search_haystack(product: dict) -> str:
    searchable_parts = [
        str(product.get("folder", "")),
        str(product.get("price", "")),
        str(product.get("material", "")),
        str(product.get("length", "")),
        str(product.get("care", "")),
    ]
    return " ".join(part for part in searchable_parts if part).lower()


def build_display_name(folder_name: str) -> str:
    parts = folder_name.rsplit("_", 3)
    if len(parts) == 4 and parts[-1].isdigit() and parts[-2].isdigit():
        base_name = parts[0]
        variant_suffix = "_".join(parts[1:])
        return f"{base_name} ({variant_suffix})"
    return folder_name


def search_products(query: str, limit: int = 3):
    normalized_query = normalize_query(query)
    if not normalized_query:
        return []

    products = load_products()
    query_lower = normalized_query.lower()
    results = []
    for p in products:
        folder = p.get("folder", "")
        if query_lower in _build_search_haystack(p):
            thumb_filename = thumbnail_filename_for_product(folder)
            thumb_path = THUMBNAILS_DIR / thumb_filename
            thumb_url = f"thumbnails/{thumb_filename}" if thumb_path.exists() else None
            results.append({
                "name": build_display_name(folder),
                "price": p.get("price", "N/A"),
                "thumbnail": thumb_url,
                "ig_url": p.get("ig_url")
            })
            if len(results) >= limit:
                break
    return results


def build_twiml_message(message_text: str) -> Response:
    escaped_text = escape(message_text)
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f"    <Message>{escaped_text}</Message>\n"
        "</Response>"
    )
    return Response(content=content, media_type="text/xml")


def build_public_url(request: Request, path: str) -> str:
    return str(request.base_url).rstrip("/") + path



def format_text_search_results(results: list[dict]) -> str:
    if not results:
        return "Sorry, no products found. Try: kurti, saree, or salwar"

    lines = ["LILA Fabrics:"]
    for i, result in enumerate(results, 1):
        line = f"{i}. {result['name']} - {result['price']}"
        if result.get("thumbnail"):
            line = f"{line} [{result['thumbnail']}]"
        lines.append(line)
    return "\n".join(lines)


def build_search_response(request: Request | None, query: str, limit: int = 3) -> list[dict]:
    results = search_products(query, limit=limit)
    response_items = []
    for result in results:
        thumbnail_url = result.get("thumbnail")
        if thumbnail_url and request is not None:
            thumbnail_url = build_public_url(request, "/" + thumbnail_url.lstrip("/"))
        response_items.append(
            {
                "name": result["name"],
                "price": result["price"],
                "thumbnail": thumbnail_url,
                "ig_url": result.get("ig_url"),
            }
        )
    return response_items


async def parse_webhook_message(request: Request) -> str:
    content_type = request.headers.get("content-type", "").lower()
    if "application/x-www-form-urlencoded" not in content_type and "multipart/form-data" not in content_type:
        raise HTTPException(
            status_code=415,
            detail="Unsupported content type. Expected form-encoded webhook payload.",
        )

    try:
        form = await request.form()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Malformed form payload.") from exc

    message = normalize_query(str(form.get("Body", "")))
    if not message:
        raise HTTPException(status_code=400, detail="Missing Body field in webhook payload.")
    return message


LOCAL_CHAT_TESTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LILA Catalog Tester</title>
  <style>
    :root {
      color-scheme: light;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background: #f6f1ea;
      color: #2e241d;
    }
    body {
      margin: 0;
      min-height: 100vh;
      background: linear-gradient(180deg, #f9f4ee 0%, #efe2d2 100%);
      display: grid;
      place-items: center;
      padding: 24px;
    }
    .app {
      width: min(760px, 100%);
      background: rgba(255, 252, 247, 0.92);
      border: 1px solid #dbc8b7;
      border-radius: 18px;
      box-shadow: 0 24px 60px rgba(90, 62, 39, 0.14);
      overflow: hidden;
    }
    .header {
      padding: 20px 24px 14px;
      border-bottom: 1px solid #ead9ca;
      background: rgba(255, 248, 239, 0.95);
    }
    .header h1 {
      margin: 0 0 6px;
      font-size: 1.35rem;
    }
    .header p {
      margin: 0;
      color: #6b5848;
      font-size: 0.95rem;
    }
    .messages {
      padding: 20px;
      min-height: 320px;
      max-height: 60vh;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
      background: rgba(255, 252, 247, 0.6);
    }
    .bubble {
      max-width: 85%;
      border-radius: 16px;
      padding: 12px 14px;
      line-height: 1.45;
      white-space: pre-wrap;
    }
    .bubble.user {
      align-self: flex-end;
      background: #70533f;
      color: #fff7ef;
    }
    .bubble.assistant {
      align-self: flex-start;
      background: #fffaf4;
      border: 1px solid #e5d4c5;
      color: #30251d;
    }
    .result {
      display: grid;
      gap: 6px;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid #eee0d3;
    }
    .result:first-of-type {
      margin-top: 0;
      padding-top: 0;
      border-top: none;
    }
    .price {
      font-weight: 600;
      color: #7b4b15;
    }
    .thumb a {
      color: #775437;
      text-decoration: none;
    }
    .thumb a:hover {
      text-decoration: underline;
    }
    .composer {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      padding: 16px 20px 20px;
      border-top: 1px solid #ead9ca;
      background: rgba(255, 248, 239, 0.95);
    }
    input, button {
      font: inherit;
    }
    input {
      border: 1px solid #d4bba7;
      border-radius: 12px;
      padding: 12px 14px;
      background: #fffdf9;
    }
    button {
      border: none;
      border-radius: 12px;
      padding: 12px 18px;
      background: #5d4332;
      color: #fff7ef;
      cursor: pointer;
    }
    button:disabled {
      opacity: 0.6;
      cursor: wait;
    }
  </style>
</head>
<body>
  <main class="app">
    <section class="header">
      <h1>LILA Catalog Tester</h1>
      <p>Find fabrics by name, material, price, or care instructions. This demo uses fictional products.</p>
    </section>
    <section class="messages" id="messages" aria-live="polite">
      <div class="bubble assistant">Try a local query like "kurti", "RM", "cotton", or "Hand wash".</div>
    </section>
    <form class="composer" id="composer">
      <input aria-label="Search the catalog" maxlength="200" id="query" name="query" type="text" placeholder="Type a catalog query..." autocomplete="off" required>
      <button id="send" type="submit">Search</button>
    </form>
  </main>
  <script>
    const messages = document.getElementById("messages");
    const form = document.getElementById("composer");
    const queryInput = document.getElementById("query");
    const sendButton = document.getElementById("send");

    function appendBubble(role, text, results) {
      const bubble = document.createElement("div");
      bubble.className = `bubble ${role}`;
      bubble.textContent = text;
      if (Array.isArray(results) && results.length) {
        results.forEach((item) => {
          const wrapper = document.createElement("div");
          wrapper.className = "result";

          const name = document.createElement("div");
          name.textContent = item.name;
          wrapper.appendChild(name);

          const price = document.createElement("div");
          price.className = "price";
          price.textContent = item.price || "N/A";
          wrapper.appendChild(price);

          if (item.thumbnail) {
            const thumbLink = document.createElement("a");
            thumbLink.href = item.thumbnail;
            thumbLink.target = "_blank";
            thumbLink.rel = "noreferrer";
            const thumbImg = document.createElement("img");
            thumbImg.src = item.thumbnail;
            thumbImg.alt = "Product thumbnail";
            thumbImg.style.maxWidth = "200px";
            thumbImg.style.borderRadius = "8px";
            thumbImg.style.display = "block";
            thumbImg.style.marginTop = "6px";
            thumbLink.appendChild(thumbImg);
            wrapper.appendChild(thumbLink);
          }

          if (item.ig_url) {
            const igLink = document.createElement("a");
            igLink.href = item.ig_url;
            igLink.target = "_blank";
            igLink.rel = "noreferrer";
            igLink.textContent = "View on Instagram";
            igLink.style.display = "inline-block";
            igLink.style.marginTop = "8px";
            igLink.style.color = "#E1306C";
            igLink.style.textDecoration = "none";
            igLink.style.fontWeight = "500";
            wrapper.appendChild(igLink);
          }

          bubble.appendChild(wrapper);
        });
      }
      messages.appendChild(bubble);
      messages.scrollTop = messages.scrollHeight;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const query = queryInput.value.trim();
      if (!query) {
        return;
      }

      appendBubble("user", query);
      queryInput.value = "";
      sendButton.disabled = true;

      try {
        const response = await fetch("/api/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, limit: 3 })
        });
        if (!response.ok) {
          throw new Error(`Search request failed (${response.status})`);
        }
        const data = await response.json();
        if (!Array.isArray(data.results) || data.results.length === 0) {
          appendBubble("assistant", "No products found. Try kurti, saree, RM, or cotton.");
        } else {
          appendBubble("assistant", `Found ${data.count} result(s):`, data.results);
        }
      } catch (error) {
        appendBubble("assistant", `Search failed: ${error.message}`);
      } finally {
        sendButton.disabled = false;
        queryInput.focus();
      }
    });
  </script>
</body>
</html>
"""


@app.post("/api/search")
async def api_search(payload: SearchRequest, request: Request):
    query = normalize_query(payload.query)
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    results = build_search_response(request, query, limit=payload.limit)
    return {"query": query, "count": len(results), "results": results}


@app.get("/", response_class=HTMLResponse)
@app.get("/tester", response_class=HTMLResponse)
def local_browser_chat_tester():
    return HTMLResponse(content=LOCAL_CHAT_TESTER_HTML)


@app.post("/api/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    message = await parse_webhook_message(request)
    results = build_search_response(request, message)
    return build_twiml_message(format_text_search_results(results))

@app.get("/api/health")
def health(request: Request):
    return {
        "status": "ok",
        "service": "lila-backend",
        "app": "LILA Fabrics Online Store",
        "mode": "synthetic-demo",
        "products": len(load_products()),
    }


