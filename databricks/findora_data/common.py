import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing source timestamp")
    parsed = datetime.fromisoformat(value.replace(" UTC", "+00:00").replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def identity(*values):
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()[:32]


def http_url(value):
    if not isinstance(value, str):
        return False
    try:
        parts = urlsplit(value)
        return parts.scheme in {"http", "https"} and bool(parts.hostname) and not parts.username
    except ValueError:
        return False


def merchant_url(value):
    if not http_url(value):
        return False
    host = urlsplit(value).hostname.lower()
    return not (host == "serpapi.com" or host.endswith(".serpapi.com")
                or re.search(r"(^|\.)google\.[a-z.]+$", host))


def google_redirect_url(value):
    """Make known Google redirect links clickable; never guess the merchant URL."""
    if not isinstance(value, str):
        return None
    candidate = "https://www.google.com" + value if value.startswith(("/goto?", "/url?")) else value
    if not http_url(candidate):
        return None
    parts = urlsplit(candidate)
    if parts.hostname in {"google.com", "www.google.com"} and parts.path in {"/goto", "/url"} and parts.query:
        return candidate
    return None


def load_products(path, allow_empty=False):
    products = json.loads(Path(path).read_text())
    if not isinstance(products, list) or (not products and not allow_empty):
        raise ValueError("Add at least one product to config/products.json; see README.md")
    seen = set()
    for product in products:
        for key in ("product_id", "title", "query", "brand", "model", "category", "color", "size", "condition", "currency"):
            if not isinstance(product.get(key), str) or not product[key].strip():
                raise ValueError(f"Every product needs a nonempty {key}")
        pid = product["product_id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,99}", pid) or pid in seen:
            raise ValueError("Product IDs must be unique, stable lowercase identifiers")
        if product["currency"] != "USD" or product["condition"] != "new":
            raise ValueError("MVP supports USD and new items only")
        if product.get("image_url") and not http_url(product["image_url"]):
            raise ValueError("image_url must be an HTTP(S) URL")
        seen.add(pid)
    return products


def load_envelopes(directory):
    files = sorted(Path(directory).rglob("*.json"))
    if not files:
        raise ValueError("No collector response files found")
    return [json.loads(path.read_text()) for path in files]
