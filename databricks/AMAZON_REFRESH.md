# Known-ASIN Amazon refresh

This branch ports only the Amazon detail adapter onto main c01c991. It preserves
main's unified pipeline, catalog defaults, and approval registry. No discovery-branch
approval corrections or older persistence code are imported.

From databricks/, one request without automatic retries:

```bash
python3 -m findora_data.amazon_detail --asin B01M0PENYV --env-file /path/to/private/.env
```

For an already-saved targeted response, use `--input /path/to/response.json` instead
of --asin. This makes no network request. Output is data/amazon_refresh/amazon_<id>.json.
Keep the raw files out of Git. After the adapter is integrated, upload the envelope
alongside the complete raw archive in the configured catalog's Volume responses folder.
Do not upload experimental retailer search reports.

The saved observation at 2026-11-15T13:42:31Z reports selected Black, Medium, Number
of Items 1; Gildan G18000; USD 10.96; In Stock; shipper/seller Amazon.com. Selected
ASIN B01M0PENYV differs from details ASIN B0D14PTTPL. Generic special_size is large,
while selected Size is Medium. These conflicts are preserved in amazon_evidence.
Candidate: 0d3fc8c37295c7f46cc376e127df89f0.

Approval remains pending. The existing exact-variant approval fields are required;
any reviewer accepting the selected-variant evidence despite those metadata conflicts
must explain the decision in evidence_notes and include acknowledged_source_conflicts:
["details_asin_differs", "details_size_differs"]. Missing/mismatched selected options,
unknown seller, stock, invalid price or inconsistent selected ASIN still block approval.
Do not assume a parent/child ASIN relationship. Price excludes unverified shipping/tax.

Cloud verification is pending. Local validation on unified main: 72 tests pass;
offline conversion produces one review candidate and zero approved offers. The raw
observation and old historical prices are not rewritten when a refresh occurs.

## New observation reviewed on this branch

The new candidate is now approved via agent inspection of the provider's explicit
selected options and single-offer evidence, with both metadata conflicts acknowledged
and rationale retained in evidence_notes. This supersedes the pending-review statement
above for this candidate only. The earlier manual Amazon candidate remains disabled;
Columbia's existing approval is preserved. One local normalized offer at USD 10.96;
replaying the same response twice produces one offer, not two.

Before running ingestion with this branch's approvals, upload
`amazon_0d3fc8c37295c7f46cc376e127df89f0.json` from local `data/amazon_refresh/` to
`/Volumes/findora_hackathon/bronze/serpapi_raw/responses` (or the actual configured
catalog's responses folder). Retain the full existing archive, including Columbia.
An approval without its raw response will correctly fail ingestion. No warehouse
start or cloud write was performed. Main remains unchanged until explicitly merged.
