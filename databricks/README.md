# B: SerpAPI → Databricks setup

**Recommended after the workspace ZIP import error: [GIT_SETUP.md](GIT_SETUP.md).**
Clone the existing repository in Databricks, select `codex/databricks-serpapi`,
and upload the saved JSON files separately into the Volume. No new GitHub repo is needed.

**Using Databricks directly without Git? Start with [UPLOAD.md](UPLOAD.md).**
Build the code-and-snapshots ZIP with `python3 -m findora_data.package_upload`,
then import it into your workspace folder and run `01_ingest` on serverless compute.
The local private `.env` file is excluded; no API key is needed for the upload notebook.

This implementation collects real provider responses, queues offers for explicit
variant review, and builds the agreed Bronze/Silver/Gold tables. It includes a
small read-only Databricks App. Local checks and validation of the initial real collection
pass; notebook execution, permissions, backend integration, and deployment are not yet verified.

## What you need to do first

1. Open your Databricks Free Edition workspace. Record its workspace URL.
2. Open Catalog Explorer. The proposed shared catalog is `findora_hackathon`
   (owned by B; confirm with the backend owner before switching).
3. Open SQL Warehouses and record the warehouse ID and connection HTTP path.
4. Create/sign in to your SerpAPI account and check your remaining search allowance.
   Keep the API key in your terminal environment or private gitignored `databricks/.env`,
   not in chat or tracked source code. The collector reads this file automatically.
5. Review `config/products.json`. The starting targets are men's black, M Regular:
   Columbia Watertight II jacket, Columbia Marquam Peak Fusion II parka, and
   Carhartt K121 sweatshirt. These are search targets, not verified offers or inventory.
   Reference URLs identify the style; a URL may default to another size.

Brand source pages used to identify those styles:
- [Columbia 1533891](https://www.columbia.com/p/mens-watertight-ii-rain-jacket-1533891.html)
- [Columbia 2088121](https://www.columbia.com/p/mens-marquam-peak-fusion-ii-hooded-parka-2088121.html?color=011)
- [Carhartt K121](https://www.carhartt.com/product/K121-BLKLREG/loose-fit-midweight-hoodie)

Confirm these canonical IDs with C before integrating them into API/UI fixtures.
Once ingested, do not reuse an ID for another size, color, or style. Add a new ID instead.

## 1. Collect locally (Python 3.10+, no extra packages)

Run these commands from the repository's `databricks` directory:

```bash
python3 -m unittest discover -s tests -v
python3 -m findora_data.collect --dry-run

# Bash: paste the key into this hidden prompt, not into the command itself.
read -rsp 'SerpAPI key: ' SERPAPI_API_KEY
export SERPAPI_API_KEY

python3 -m findora_data.collect --max-requests 9 --details-per-product 2
unset SERPAPI_API_KEY
```

Three discovery searches plus up to two product-detail calls each means at most
nine HTTP requests for the configured targets. Pagination and extra-store fetches
are intentionally excluded. Missing detail tokens result in fewer calls. A failed
request stops the run; earlier responses remain saved. There are no automatic paid
retries. The provider decides billing; consult your actual allowance.

`data/raw/*.json` contains provider responses and collection metadata. `data/` is
gitignored. API keys are stripped before writing. Preserve the full raw directory.
The collector uses `google_shopping`, then `google_immersive_product` for candidates
with tokens. Search ordering is not an exact-match guarantee.

By default provider caching is allowed. `--fresh` bypasses caching and can consume
additional quota. Re-fetching cached results is not new history: the source search
ID and source timestamp determine observation identity, not your upload time.

## 2. Review exact matches

```bash
python3 -m findora_data.review
```

This creates `data/review_queue.json`. It will not overwrite an existing queue;
use `--output data/review_queue_2.json` on later runs.

For a suitable candidate:

1. Open `product_url` and select the target's size, color, and regular/tall fit.
2. Verify the brand, manufacturer style/model, new condition, USD price, and availability.
   Check that the source price actually applies to this variant without a required
   membership or unverified coupon. If it differs, leave this candidate unapproved
   and collect a new response. Never edit source prices to make them match.
3. Copy its review object into the array in `config/approvals.json`.
4. Fill `confirmed_attributes` with the verified target values for `brand`, `model`,
   `color`, `size`, `condition`, and `currency`. These must match `config/products.json`.
5. Set `evidence_url` to the merchant page and write `evidence_notes` describing what
   confirms the variant and price. Fill `reviewed_at` with the actual UTC review time.
6. Set `confirmed`, `price_verified`, and `available` to `true` only after those checks.

Some real store responses use Google's opaque `/goto?url=...` redirect format.
For `merchant_redirect_requires_resolution`, open the queue's absolute `review_url`
in your browser. Copy the actual destination into `resolved_product_url` and the
original `review_url` into `resolved_from` in the approval object. Verify that the
destination is the correct merchant/product/variant, and use its page for
`evidence_url`. A resolved URL alone does not establish size, color, price, or stock.
Never replace a wrong-variant destination with a guessed URL. Bronze preserves
the original redirect; Silver uses the reviewed destination and records both.

The review queue deliberately leaves verification fields blank. Other candidates with
`problems` cannot enter Silver. Google Shopping search links are discovery links, not
merchant offer URLs; use detail results with merchant links. Unknown fields stay
unknown. We do not infer the selected size from a query or trust an LLM to establish it.

Validate edited approvals without more network calls:

```bash
python3 -m findora_data.review --output data/review_validated.json
```

Only explicitly approved observations enter `silver.normalized_offers`; unreviewed
candidates remain in Bronze and the review queue. Each new source observation needs
its own review. Removing an approval retracts that offer on the next complete rebuild.
Keep prior approvals and raw responses to retain real history. This manual review is
intended for a small hackathon catalog; automatic variant verification is future work.

For additional similar products, add separate real products to the manifest and
review their offers. C owns similarity ranking. Three products in three categories
are only initial collection targets, not evidence that two suitable alternatives
exist for every target.

## 3. Upload code and raw responses to Free Edition

Use an existing catalog you can write to; no custom catalog or classic cluster is required.

1. Upload the `databricks` source directory to your Databricks workspace, preserving
   `findora_data/`, `config/`, `notebooks/`, `app/`, and `sql/`. Exclude `data/` and
   `__pycache__/`. Alternatively sync these local changes through your team's Git
   workflow before cloning/pulling a Databricks Git folder. These changes have not
   been pushed automatically.
2. Open/import `notebooks/01_ingest.py` as a Python notebook and attach serverless compute.
3. Set `project_root` to the workspace path ending in `/databricks`.
4. Set `catalog` to the proposed shared catalog `findora_hackathon` (confirm
   with the backend owner before switching).
5. Run only the first code cell. It creates schemas, empty Delta tables, and the Volume.
6. In Catalog Explorer, open `<catalog>.bronze.serpapi_raw`. Create a `responses`
   directory and upload **all** collected JSON files there. The printed path is:

   ```text
   /Volumes/<catalog>/bronze/serpapi_raw/responses
   ```

7. Ensure the workspace copy of `config/approvals.json` includes your review work.
8. Run the remaining notebook cells. Empty approvals produce Bronze rows and zero
   exact offers, which is expected until review is complete.
9. Run again on the same inputs: Bronze and Silver counts must not grow.
10. Run `sql/validation.sql`, replacing the initial catalog with your actual one.
    Save counts and sample query results in `docs/progress/databricks.md`.

The MVP reads a small archive into driver memory. Keep it to tens of products and
small responses. This is not a bulk crawler. Collect locally to avoid Free Edition
outbound-network restrictions; Databricks still performs persistence and Gold SQL.

The rebuild refuses to proceed if old Bronze candidates are missing from the uploaded
archive or existing canonical identities change. Silver is synchronized with the full
review set, including removal of revoked approvals. Do not run competing ingestion jobs.

## 4. What C should query

Existing shared contract files and backend routes remain unchanged. The following
semantics are B's implementation proposal for C to confirm before integration:

| Object | Meaning |
|---|---|
| `gold.product_catalog` | Canonical products, attributes, and `observed`/`insufficient` status |
| `gold.product_offers` | All valid reviewed historical observations, `source_type=snapshot` |
| `gold.current_offers` | Latest observation per product/retailer, at most 24 hours old |
| `gold.price_summary` | Contract columns; current minimum plus historical minimum/median/count |
| `gold.price_coverage` | First/last observation and number of distinct UTC dates |

`lowest_observed_price` is the minimum of current offers, or NULL if all are stale.
`minimum_observed_price` and `median_observed_price` cover all reviewed retailer-time
observations. `observation_count` counts those rows, **not dates or independent market
samples**; more sampled retailers can affect the median. These statistics alone do
not authorize BUY/WAIT advice. C must gate advice on distinct dates, span, and current
coverage. The app uses a conservative minimum of 3 dates and 48 hours just to indicate
that historical comparisons are available; it does not issue a buying recommendation.

All values are listed prices; shipping/tax totals are not asserted. Everything is
a timestamped snapshot, including recently collected data. `product_url` maps to
the API's `url` field. Convert timestamps to UTC ISO-8601 at the API boundary.
Use bound SQL parameters for IDs, never string interpolation of user input.

See `sql/backend_queries.sql` for exact query examples. Hand C:
- Workspace hostname, SQL warehouse HTTP path, actual catalog, and Gold object names.
- The canonical product IDs and returned example rows.
- Access via C's own authorized identity/credentials; no secrets in shared docs.
- A successful offers query and evidence of a second run with stable counts.

## 5. Deploy the companion Databricks App

1. Create a Databricks App, using the contents of `databricks/app` as its source root.
   `app.yaml`, `app.py`, and `requirements.txt` must be together at that root.
2. Add a SQL warehouse resource with key `sql-warehouse` and **Can use** permission.
3. Set `FINDORA_CATALOG` in `app.yaml` to the catalog used by the notebook.
4. Find the App's service principal in its settings. Grant it `USE CATALOG`,
   `USE SCHEMA` on Gold, and `SELECT` on the Gold views. Use the same scope for C's
   query identity. The warehouse resource does not itself grant table permissions.
5. Deploy. The app uses its own service-principal authentication; it needs no SerpAPI
   key or hardcoded Databricks token.
6. Open its URL, select a product, verify actual offers/history, and check access using
   the judge/teammate identity. Do not assume the App URL is publicly accessible.
7. Record the URL and verification evidence. Free Edition Apps stop after 24 hours;
   restart/check before judging. Observe compute quotas.

Example grants, run by the data owner; replace both placeholders first:

```sql
GRANT USE CATALOG ON CATALOG `<catalog>` TO `<app-service-principal>`;
GRANT USE SCHEMA ON SCHEMA `<catalog>`.gold TO `<app-service-principal>`;
GRANT SELECT ON SCHEMA `<catalog>`.gold TO `<app-service-principal>`;
```

## Verification status and sources

Local tests cover cached-response deduplication, mismatched variants, currency,
invalid prices, review evidence, request limits, redaction, and partial collection
failure. They use clearly synthetic fixtures confined to `tests/`; no artificial
prices are included in the default data. The user has run the collector: 11 saved
responses across two batches yield 130 unique candidates, with zero approved offers so far.
Spark/Delta execution, warehouse queries, and App deployment must be verified in
your workspace. Local Python compilation is not evidence of a working cloud deployment.

Official references checked while implementing:
- [SerpAPI Shopping](https://serpapi.com/google-shopping-api)
- [SerpAPI Shopping result fields](https://serpapi.com/shopping-results)
- [SerpAPI Immersive Product](https://serpapi.com/google-immersive-product-api)
- [Databricks Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
- [Databricks Streamlit tutorial and authentication](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/tutorial-streamlit)
- [App SQL warehouse resource](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/sql-warehouse)
- [App runtime configuration](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/app-runtime)
