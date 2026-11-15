"""Run from databricks/: python3 -m findora_data.collect --dry-run."""
import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

from .common import load_products, utc_now


class CollectionError(RuntimeError):
    pass


def load_api_key(env_file=None):
    """Read only our key; no shell execution or variable interpolation."""
    key = os.environ.get("SERPAPI_API_KEY", "").strip()
    if key:
        return key
    path = Path(env_file) if env_file is not None else Path(__file__).resolve().parent.parent / ".env"
    if not path.is_file():
        return ""
    found = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if separator and name.strip() == "SERPAPI_API_KEY":
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            found.append(value.strip())
    if len(found) > 1:
        raise ValueError("Keep only one SERPAPI_API_KEY entry in the private .env file")
    return found[0] if found else ""


def redact(value, secret):
    if isinstance(value, dict):
        return {k: redact(v, secret) for k, v in value.items()
                if k.lower() not in {"api_key", "authorization"}}
    if isinstance(value, list):
        return [redact(v, secret) for v in value]
    if isinstance(value, str):
        value = value.replace(secret, "[REDACTED]") if secret else value
        return re.sub(r"(?i)(api_key=)[^&\s]+", r"\1[REDACTED]", value)
    return value


def fetch(params, api_key):
    request = Request("https://serpapi.com/search.json?" + urlencode({**params, "api_key": api_key}),
                      headers={"User-Agent": "Findora-Hackathon/1.0"})
    try:
        with urlopen(request, timeout=45) as response:
            payload = json.load(response)
    except HTTPError as exc:
        # Never print exception URLs: they contain the API key.
        raise CollectionError(f"SerpAPI HTTP {exc.code}; check quota/key/network") from None
    except (URLError, TimeoutError, ValueError, OSError):
        raise CollectionError("SerpAPI request failed; no automatic paid retry") from None
    if not isinstance(payload, dict) or payload.get("error") or payload.get("search_metadata", {}).get("status") != "Success":
        raise CollectionError("SerpAPI did not return a successful result; check the provider dashboard")
    return redact(payload, api_key)


def product_lookup_targets(payload, product):
    """Ordered google_product lookup params from discovery rows, best first.

    Prefers the provider's own prebuilt product-API link token (it addresses the
    exact discovered listing; product_id lookups often return no results), then
    the provider product ID. Rows whose title mentions the target color and size
    are tried first — a candidate-ordering heuristic only, never an exact match.
    The embedded api_key in prebuilt links is never copied into request params.
    """
    color = str(product.get("color") or "").casefold().strip()
    size = str(product.get("size") or "").casefold().split()[0] if product.get("size") else ""
    rows = payload.get("shopping_results", [])

    def variant_rank(row):
        title = str(row.get("title") or "").casefold()
        has_color = bool(color) and color in title
        has_size = bool(size) and re.search(rf"\b{re.escape(size)}\b", title) is not None
        return 0 if has_color and has_size else 1

    order = sorted(range(len(rows)), key=lambda i: (variant_rank(rows[i]), i))
    targets, seen = [], set()
    for i in order:
        row = rows[i]
        params = None
        link = row.get("serpapi_product_api") or ""
        query = parse_qs(urlsplit(link).query) if link else {}
        token = query.get("page_token", [None])[0]
        if token:
            params = {"engine": "google_product", "page_token": token}
        elif row.get("product_id"):
            params = {"engine": "google_product", "product_id": str(row["product_id"])}
        if params:
            key = json.dumps(params, sort_keys=True)
            if key not in seen:
                seen.add(key)
                targets.append(params)
    return targets


def collect(products, output, api_key, max_requests=12, details_per_product=2, fresh=False,
            product_lookups=0, fetcher=fetch):
    if max_requests < len(products) or details_per_product < 0 or product_lookups < 0:
        raise ValueError("Budget must cover at least one search per product; limits cannot be negative")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    batch = uuid.uuid4().hex
    used = 0

    def request(product, params):
        nonlocal used
        used += 1
        if fresh:
            params = {**params, "no_cache": "true"}
        payload = redact(fetcher(params, api_key), api_key)
        envelope = {"format_version": 1, "source_type": "snapshot", "batch_id": batch,
                    "target_product_id": product["product_id"], "market": "us",
                    "fetched_at": utc_now(), "request": params, "response": payload}
        # Each successful response survives even if a later request fails.
        path = output / f"{batch}_{used:03d}.json"
        path.write_text(json.dumps(envelope, indent=2) + "\n")
        return payload

    for index, product in enumerate(products):
        payload = request(product, {"engine": "google_shopping", "q": product["query"], "gl": "us", "hl": "en"})
        tokens = list(dict.fromkeys(row["immersive_product_page_token"]
                      for row in payload.get("shopping_results", [])
                      if row.get("immersive_product_page_token")))
        # Reserve one discovery call for each remaining target.
        remaining_targets = len(products) - index - 1
        detail_budget = min(details_per_product, max_requests - used - remaining_targets)
        for token in tokens[:detail_budget]:
            request(product, {"engine": "google_immersive_product", "page_token": token})
        # Google Product detail lookup via the provider's prebuilt tokens/IDs
        # (query fallback). Store rows may describe the default variant, so they
        # only ever enter the review queue; ordering never claims an exact match.
        lookup_targets = product_lookup_targets(payload, product)
        if not lookup_targets:
            lookup_targets = [{"engine": "google_product", "q": product["query"]}]
        lookup_budget = min(product_lookups, max_requests - used - remaining_targets)
        for params in lookup_targets[:lookup_budget]:
            request(product, params)
    return used


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", default="config/products.json")
    parser.add_argument("--output", default="data/raw")
    parser.add_argument("--max-requests", type=int, default=12)
    parser.add_argument("--details-per-product", type=int, default=2)
    parser.add_argument("--product-lookups", type=int, default=0,
                        help="Google Product detail lookups per product (uses discovery product IDs)")
    parser.add_argument("--fresh", action="store_true", help="Bypass provider cache; consumes search quota")
    parser.add_argument("--dry-run", action="store_true", help="Validate targets and budget without network or key")
    args = parser.parse_args()
    try:
        products = load_products(args.products)
        if args.max_requests < len(products) or args.details_per_product < 0 or args.product_lookups < 0:
            raise ValueError("Request budget is too small or a lookup limit is negative")
        upper = min(args.max_requests, len(products) * (1 + args.details_per_product + args.product_lookups))
        print(f"Targets: {len(products)}; request ceiling: {upper}")
        if args.dry_run:
            return
        key = load_api_key()
        if not key:
            raise ValueError("Set SERPAPI_API_KEY in your environment or private databricks/.env file")
        used = collect(products, args.output, key, args.max_requests, args.details_per_product,
                       args.fresh, args.product_lookups)
        print(f"Saved {used} successful response files to {args.output}")
    except (ValueError, OSError, CollectionError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
