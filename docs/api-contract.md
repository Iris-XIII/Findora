# API contract v0.1 — change only by team agreement

Base URL local: `http://localhost:8000`. All prices USD in demo. All responses JSON. IDs are stable strings. No fabricated live prices.

| Route | Response | MVP |
|---|---|---|
| `GET /health` | `{status, data_mode}` | P0 |
| `GET /products/search?q=...` | `{items: Product[]}` | P0 |
| `GET /products/{id}` | `Product` | P0 |
| `GET /products/{id}/offers` | `{product_id, offers: Offer[]}` | P0 |
| `GET /products/{id}/history` | `{product_id, observations: Observation[], data_status}` | P0 |
| `GET /products/{id}/similar` | `{product_id, items: SimilarProduct[]}` | P0 |
| `GET /products/{id}/advice` | `{product_id, decision, explanation, evidence, data_status}` | P0 |

`Product`: `product_id`, `title`, `brand`, `category`, `image_url` (nullable), `description` (nullable), `data_status`.

`Offer`: `offer_id`, `retailer`, `price` (number), `currency`, `url`, `observed_at`, `match_type` (`exact`/`unverified`), `source_type` (`live`/`snapshot`/`demo`).

`Observation`: `observed_at`, `price`, `currency`, `retailer`, `source_type`.

`SimilarProduct`: `product_id`, `title`, `brand`, `price` (nullable), `reason`.

`decision`: `BUY`, `WAIT_OR_COMPARE`, `INSUFFICIENT_DATA`. `data_status`: `demo`, `observed`, `insufficient`. All demo responses must have `data_status=demo` and demo offers `source_type=demo`.

### Mock example
```json
{
  "product_id": "demo-headphones-a",
  "offers": [{
    "offer_id": "demo-offer-1",
    "retailer": "Example Retailer",
    "price": 129.99,
    "currency": "USD",
    "url": "https://example.com/item",
    "observed_at": "2026-11-14T12:00:00Z",
    "match_type": "exact",
    "source_type": "demo"
  }]
}
```

`example.com` is placeholder only. Do not display as a real store offer.
