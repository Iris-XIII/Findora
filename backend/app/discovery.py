"""Optional one-request shopping discovery, separate from reviewed Databricks offers.

A pasted URL is used to build search keywords; the backend NEVER requests that URL.
Search results are candidates, not verified exact-variant offers or price history.
"""
from collections import deque
from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
import json
import os
import re
from threading import Lock
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen


STOP_WORDS = {
    'www', 'com', 'html', 'htm', 'shop', 'products', 'product', 'collections',
    'collection', 'p', 'dp', 'gp', 'item', 'items', 'buy', 'us', 'en', 'detail',
    'clothing', 'apparel', 'women', 'womens', 'men', 'mens', 'search',
}


def interpret_search(value):
    """Return (input_type, query for provider, retailer host), without fetching URLs."""
    text = value.strip()
    if not re.match(r'^https?://', text, re.I):
        text = re.sub(r'\bcolumina\b', 'columbia', text, flags=re.I)
        return 'text', ' '.join(text.split()), None
    try:
        url = urlsplit(text)
        host = (url.hostname or '').lower()
        url.port  # Validate malformed port syntax without opening the URL.
    except ValueError:
        return 'url', '', None
    if url.username or url.password:
        return 'url', '', None
    if url.scheme.lower() not in ('http', 'https') or not host or '.' not in host:
        return 'url', '', None
    # Product slugs usually contain more information than the retailer name.
    parts = []
    for segment in unquote(url.path).split('/'):
        terms = re.findall(r'[a-zA-Z0-9]+', segment.lower())
        if terms:
            parts.append(terms)
    tail = parts[-3:]
    tokens = [t for part in tail for t in part if t not in STOP_WORDS]
    # URL search parameters are NOT forwarded: only whitelisted product options.
    options = parse_qs(url.query)
    for key in ('color', 'size', 'style', 'model'):
        for item in options.get(key, [])[:1]:
            tokens.extend(re.findall(r'[a-zA-Z0-9]+', item.lower())[:4])
    # Keep useful identifying ASIN/model strings, but don't pass through tracking params.
    tokens = list(dict.fromkeys(tokens))[:18]
    return 'url', ' '.join(tokens)[:180], host


def https_link(raw):
    """Only present ordinary HTTPS links in the UI; never trust provider URLs blindly."""
    if not isinstance(raw, str) or len(raw) > 2000:
        return None
    try:
        url = urlsplit(raw)
        if url.scheme != 'https' or not url.hostname or '.' not in url.hostname or url.username or url.password:
            return None
        return raw
    except ValueError:
        return None


def provider_request(query, api_key):
    params = urlencode({'engine': 'google_shopping', 'q': query, 'gl': 'us', 'hl': 'en', 'api_key': api_key})
    req = Request('https://serpapi.com/search.json?' + params,
                  headers={'User-Agent': 'Findora-Hackathon/1.0'})
    # Do not log exceptions or URLs: the request URL contains a secret.
    with urlopen(req, timeout=12) as response:
        return json.load(response)


def price_or_none(value):
    try:
        if isinstance(value, bool) or value is None:
            return None
        n = float(value)
        return round(n, 2) if isfinite(n) and n > 0 else None
    except (ValueError, TypeError):
        return None


class Discovery:
    """Bounded on-demand SerpApi search; memory-only cache, no approval writes."""

    def __init__(self, key=None, fetcher=provider_request, max_requests=20, cache_seconds=600):
        self.key = (os.getenv('SERPAPI_API_KEY', '') if key is None else key).strip()
        self.fetcher = fetcher
        self.max_requests = max_requests
        self.cache_seconds = cache_seconds
        self.calls = deque()
        self.cache = {}
        self.lock = Lock()
        # A small process-wide budget: serialize searches so simultaneous identical
        # queries reuse the completed cache entry instead of billing twice.
        self.search_lock = Lock()

    def search(self, raw_query):
        with self.search_lock:
            return self._search(raw_query)

    def _search(self, raw_query):
        kind, query, host = interpret_search(raw_query)
        base = {
            'query': raw_query, 'input_type': kind,
            'interpreted': {'terms': query.lower().split(), 'retailer_host': host, 'category': None},
            'catalog_matches': [], 'discovered': [], 'similar': [],
            'discovery_status': 'unavailable', 'notices': [],
        }
        if len(query) < 3:
            base.update(discovery_status='insufficient_query', notices=[
                'This URL does not contain enough product information. Try the product name or style number.'
            ])
            return base
        if not self.key:
            base['notices'].append('Live discovery is not configured. Existing catalog products remain available.')
            return base
        cache_key = query.casefold()
        with self.lock:
            now = monotonic()
            self.cache = {k: v for k, v in self.cache.items()
                          if now - v[0] < self.cache_seconds}
            old = self.cache.get(cache_key)
            if old and now - old[0] < self.cache_seconds:
                return {**old[1], 'discovery_status': 'cached', 'query': raw_query, 'input_type': kind,
                        'interpreted': base['interpreted']}
            while self.calls and now - self.calls[0] >= 3600:
                self.calls.popleft()
            if len(self.calls) >= self.max_requests:
                base.update(discovery_status='budget_exhausted', notices=[
                    'Live search budget reached for this hour. Try a cached query or browse the catalog.'
                ])
                return base
            self.calls.append(now)
        try:
            payload = self.fetcher(query, self.key)
            if not isinstance(payload, dict) or payload.get('error'):
                raise ValueError('Provider error')
            results = payload.get('shopping_results', [])
            if not isinstance(results, list):
                raise ValueError('Invalid shopping results')
        except (HTTPError, URLError, TimeoutError, ValueError, OSError, TypeError):
            base['notices'].append('Live shopping search is unavailable; no fabricated results were used.')
            return base
        stamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        for result in results[:15]:
            if not isinstance(result, dict) or not isinstance(result.get('title'), str):
                continue
            title = result['title'].strip()[:250]
            if not title:
                continue
            merchant = str(result.get('source') or 'Unknown retailer')[:100]
            link = https_link(result.get('product_link')) or https_link(result.get('link'))
            # Google Shopping in gl=us normally uses USD, but an explicit foreign
            # currency overrides that assumption: never label it as USD.
            shown = str(result.get('price') or '')
            explicit = str(result.get('currency') or '').upper().strip()
            foreign = (explicit and explicit != 'USD') or any(
                token in shown.upper() for token in ('€', '£', '¥', 'EUR', 'GBP', 'CAD', 'AUD', 'C$', 'CA$', 'A$', 'AU$', '₹')
            )
            price = None if foreign else price_or_none(result.get('extracted_price'))
            problems = ['variant_not_verified']
            if foreign:
                problems.append('non_usd_price')
            if price is None:
                problems.append('missing_or_invalid_price')
            if not link:
                problems.append('missing_safe_product_link')
            link_host = urlsplit(link).hostname.lower() if link else ''
            is_google = any(link_host == domain or link_host.endswith('.' + domain)
                            for domain in ('google.com', 'google.co.uk'))
            identity = sha256(f'{title}|{merchant}|{link}'.encode()).hexdigest()[:16]
            base['discovered'].append({
                'candidate_id': 'discovered:' + identity, 'title': title,
                'retailer': merchant, 'listed_price': price, 'currency': 'USD' if price is not None else None,
                'url': link, 'url_kind': 'google_listing' if is_google else ('merchant' if link else 'none'),
                'observed_at': stamp, 'provenance': 'serpapi_google_shopping',
                'verification': 'unverified', 'problems': problems,
            })
        base['discovery_status'] = 'ok' if base['discovered'] else 'no_results'
        base['notices'].append(
            'Search listings are unverified. Confirm size, color, availability, shipping and final price at the retailer.'
            if base['discovered'] else 'No shopping candidates found; try another product name or style number.'
        )
        with self.lock:
            if len(self.cache) >= 256:
                self.cache.pop(next(iter(self.cache)))
            self.cache[cache_key] = (monotonic(), base)
        return base


def catalog_matches(query, products):
    """Small, transparent keyword match against already-served canonical products."""
    words = [w for w in re.findall(r'[a-z0-9]+', query.casefold()) if w not in STOP_WORDS]
    if not words:
        return [], []
    unique = set(words)
    scored = []
    for product in products:
        if not isinstance(product, dict) or not product.get('product_id'):
            continue
        haystack = set(re.findall(r'[a-z0-9]+',
                            ' '.join(str(product.get(k) or '') for k in ('title', 'brand', 'category')).casefold()))
        hits = unique & haystack
        if hits and (len(unique) == 1 or len(hits) >= 2):
            scored.append((len(hits) / len(unique), len(hits), product))
    scored.sort(key=lambda entry: (-entry[0], -entry[1], entry[2].get('title', '')))
    matches = [{**p, 'match_score': round(score, 2),
                'match_reason': f'{hits} of {len(unique)} query terms match catalog attributes'}
               for score, hits, p in scored[:5]]
    matched_ids = {p['product_id'] for p in matches}
    matching_categories = {p.get('category') for p in matches if p.get('category')}
    similar = [{**{k: p.get(k) for k in ('product_id', 'title', 'brand')},
                'price': None, 'reason': 'Same catalog category; variant and price not verified as an exact match.'}
               for p in products if p.get('product_id') not in matched_ids
               and p.get('category') in matching_categories][:3]
    return matches, similar
