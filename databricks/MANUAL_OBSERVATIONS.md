# Manual observations

Documented merchant-page observations are labeled `manual_snapshot`, never SerpAPI.
They require the existing exact-variant approval before becoming offers.

Prepare a private JSON file with `target_product_id` and an `observation` object.
Required observation fields: `title`, `retailer`, `source_product_id`,
`product_url` (direct merchant URL), positive numeric `price`, `currency` (`USD`),
`observed_at` (ISO timestamp with timezone), `evidence_ref`, and `evidence_notes`.
Optional fields: `observation_precision` and `reported_attributes`.
Keep observations and screenshots outside Git. Retain accessible evidence and
document model, color, size, quantity, seller, and availability. Resolve conflicting
product identifiers before approval. First-available dates and list prices are not
historical price observations.

From the `databricks` directory:

```bash
python3 -m findora_data.manual --input data/manual_observation.json
```

Upload the generated `data/raw/manual_*.json` into
`/Volumes/workspace/bronze/serpapi_raw/responses`, keeping the full existing archive.
Pull updated code in Databricks and rerun ingestion to generate the review queue.
Without approval this adds only a Bronze candidate. After exact-variant review,
update `config/approvals.json` through the normal workflow and rerun ingestion.
Reimporting the same observation preserves its identity; it does not create history.
Record whether the observed price excludes shipping and taxes in evidence notes.
