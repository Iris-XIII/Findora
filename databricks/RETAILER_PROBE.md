# Capped retailer discovery experiment

This isolated probe supplements the Google collector. Existing approvals, normalizer,
raw ingestion archive and cloud tables are not modified. It uses one Amazon search
and one Walmart search, with no retries or pagination. Each invocation can use up to
two searches; rerunning is not free by assumption.

From `databricks/`:

```bash
python3 -m findora_data.retailer_probe --dry-run
python3 -m findora_data.retailer_probe --env-file /path/to/private/.env
```

Default output: ignored `data/retailer_probe/`, NOT `data/raw/`. These envelopes are
experimental evidence, not supported ingestion inputs. Do not upload them into the
existing pipeline's responses folder. The report ranks title signals; it never approves
an offer. Marketplace is separate from seller, unknown seller stays null, and color
option links do not inherit the parent price. The ranking is heuristic and can exclude
relevant results or retain irrelevant ones; raw responses remain available for inspection.

## Executed experiment

Two requests succeeded: 60 Amazon organic results and 14 Walmart organic results.
Batch: `7be16afec5cd4f99b0304c0de5341d43`. No automatic retry or detail calls.
No newly verified Black/Medium/single-item offer from these searches alone.
Examples of leads from returned variant options (not approved offers):
- Amazon Black option ASIN B0HN8B77S4 under Gildan 18000 Heavy Blend Unisex
  Crewneck Sweatshirt. Medium, single quantity, seller and applicable price unverified.
- Walmart Black option item 790345716 under Gildan Men's Long Sleeve Crewneck
  Sweatshirt 18000. Medium and applicable price unverified. Parent search seller
  was JustBlanks; do not assume the same seller/price for another variant.

Fallback: retain the existing reviewed demo offers. Search coverage succeeded,
exact-offer verification did not. Stop spending on this experiment unless a specific
follow-up is requested. No live history or forecast was created.

Provider schemas: https://serpapi.com/amazon-search-api and
https://serpapi.com/walmart-search-api.

## Targeted Amazon lookup — November 15, 2026

One additional, explicitly requested call: engine=amazon_product,
asin=B01M0PENYV, amazon_domain=amazon.com. Succeeded. Provider observation time:
2026-11-15 13:42:31 UTC (07:42:31 America/Chicago).

Returned selected variants: Color Black, Size Medium, Number of Items 1, each
selected=true and associated with B01M0PENYV. Title/model: Gildan G18000.
Product and single purchase offer both show USD 10.96, In Stock; single-offer
shipper/seller is Amazon.com. Delivery remains conditional on membership/order value.

The SAME response reports product_results.asin B01M0PENYV and
product_details.asin B0D14PTTPL. This reproduces the user's discrepancy; it does
not prove a parent/child relationship. Generic product_details.special_size says
large while the selected Size is Medium; preserve this metadata conflict. Title
contains Multipack but the selected Number of Items and details unit count are 1.

Raw response (ignored): data/retailer_probe/targeted_83c13f4df6df4a88a551aa36c5a7ded1.json.
A sibling _comparison.json records the evidence. Existing approvals unchanged.
This new price is a separate observation, not a correction of the old screenshot
or the later branch's 10.95 correction. No normalization/cloud ingestion performed.

Conclusion: a known-ASIN detail lookup can retrieve the selected options and
purchase offer that broad search did not establish. Next implementation is a
variant-aware Amazon detail adapter with selected-ASIN/option checks, seller/stock
checks, explicit conflict reporting, and normal source timestamps. No automatic
promotion based solely on title, ASIN equality, or inherited search prices.
