"""Conservative normalization: only explicitly reviewed observations enter Silver."""
import json
import math
from urllib.parse import urlsplit

from .common import google_redirect_url, identity, merchant_url, timestamp

ATTRIBUTES = ("brand", "model", "color", "size", "condition", "currency")


def candidates(envelope):
    if envelope.get("format_version") != 1 or envelope.get("source_type") != "snapshot":
        raise ValueError("Only version 1 real snapshot envelopes are accepted")
    response = envelope["response"]
    metadata = response.get("search_metadata", {})
    if response.get("error") or metadata.get("status") != "Success" or not metadata.get("id"):
        raise ValueError("Response must have a successful source search ID")
    # Use provider time, never upload/fetch time: cached responses stay the same observation.
    observed = timestamp(metadata.get("created_at"))
    fetched = timestamp(envelope.get("fetched_at"))
    if observed > fetched:
        raise ValueError("Source timestamp is later than collection time")
    engine = envelope["request"]["engine"]
    if engine == "google_shopping":
        rows = response.get("shopping_results", [])
    elif engine == "google_immersive_product":
        rows = response.get("product_results", {}).get("stores", [])
    else:
        raise ValueError("Unsupported SerpAPI engine")
    result = []
    for index, row in enumerate(rows):
        # Shopping product_link is often a Google page. Keep it for review but never serve it as a merchant URL.
        url = row.get("link") or row.get("product_link") or ""
        price = row.get("extracted_price")
        valid_price = isinstance(price, (int, float)) and not isinstance(price, bool) and math.isfinite(price) and price > 0
        explicit_currency = row.get("currency")
        displayed_price = str(row.get("price", "")).strip()
        us_price = envelope.get("market") == "us" and displayed_price.startswith(("$", "US$", "USD"))
        currency = explicit_currency or ("USD" if us_price else None)
        title = row.get("title") or response.get("product_results", {}).get("title") or ""
        retailer = row.get("name") if engine == "google_immersive_product" else row.get("source")
        cid = identity(metadata["id"], engine, index, url, title, price)
        problems = []
        if not valid_price:
            problems.append("missing_or_invalid_price")
        if currency != "USD":
            problems.append("currency_not_confirmed_usd")
        if not merchant_url(url):
            problems.append("merchant_redirect_requires_resolution" if google_redirect_url(url) else "missing_direct_merchant_url")
        if not retailer:
            problems.append("missing_retailer")
        if not title:
            problems.append("missing_title")
        if row.get("second_hand_condition"):
            problems.append("used_or_refurbished")
        provenance = {"source": "serpapi", "engine": engine, "search_id": metadata["id"],
                      "candidate_id": cid, "source_type": "snapshot", "source_observed_at": observed.isoformat(),
                      "fetched_at": fetched.isoformat(), "target_product_id": envelope["target_product_id"],
                      "source_record_index": index}
        result.append({"candidate_id": cid, "target_product_id": envelope["target_product_id"],
                       "source_product_id": str(row.get("product_id") or metadata["id"]),
                       "title": title, "retailer": retailer or "", "price": float(price) if valid_price else None,
                       "currency": currency, "product_url": url, "observed_at": observed,
                       "batch_id": envelope["batch_id"], "provenance": provenance, "problems": problems})
    return result


def normalize(envelopes, products, approvals):
    targets = {p["product_id"]: p for p in products}
    approved = {}
    for entry in approvals:
        if entry.get("confirmed") is not True:
            continue
        cid = entry["candidate_id"]
        if cid in approved:
            raise ValueError("Duplicate approval for candidate " + cid)
        target = targets.get(entry.get("product_id"))
        if not target:
            raise ValueError("Approval refers to an unknown product")
        confirmed = entry.get("confirmed_attributes", {})
        if any(str(confirmed.get(k, "")).casefold().strip() != target[k].casefold().strip() for k in ATTRIBUTES):
            raise ValueError("Approval does not confirm all target attributes for " + cid)
        if not merchant_url(entry.get("evidence_url")) or not entry.get("evidence_notes", "").strip():
            raise ValueError("Approval requires a merchant evidence URL and variant/price verification notes")
        if entry.get("price_verified") is not True or entry.get("available") is not True:
            raise ValueError("Approval must confirm the listed price applies to an available target variant")
        timestamp(entry.get("reviewed_at"))
        approved[cid] = entry

    bronze, silver, review = {}, {}, {}
    used_approvals = set()
    for envelope in envelopes:
        if envelope.get("target_product_id") not in targets:
            raise ValueError("Raw response refers to a target missing from the product manifest")
        for row in candidates(envelope):
            cid = row["candidate_id"]
            provenance = dict(row["provenance"])
            bronze[cid] = {"source": "serpapi", "source_product_id": row["source_product_id"],
                           "raw_title": row["title"], "brand": None, "model": None, "variant": None,
                           "price": row["price"], "currency": row["currency"], "product_url": row["product_url"],
                           "observed_at": row["observed_at"], "ingestion_batch": row["batch_id"],
                           "provenance": json.dumps(provenance, sort_keys=True)}
            review[cid] = {"candidate_id": cid, "product_id": row["target_product_id"],
                           "title": row["title"], "retailer": row["retailer"], "price": row["price"],
                           "product_url": row["product_url"], "observed_at": row["observed_at"].isoformat(),
                           "review_url": google_redirect_url(row["product_url"]) or row["product_url"],
                           "resolved_product_url": "", "resolved_from": "",
                           "problems": row["problems"], "confirmed": False,
                           "price_verified": False, "available": False,
                           "confirmed_attributes": {k: "" for k in ATTRIBUTES},
                           "evidence_url": "", "evidence_notes": "", "reviewed_at": ""}
            approval = approved.get(cid)
            if not approval:
                continue
            used_approvals.add(cid)
            problems = list(row["problems"])
            served_url = row["product_url"]
            if "merchant_redirect_requires_resolution" in problems:
                resolved = approval.get("resolved_product_url")
                if not merchant_url(resolved) or approval.get("resolved_from") != google_redirect_url(row["product_url"]):
                    raise ValueError("Google redirect requires its verified merchant destination and original review_url")
                served_url = resolved
                provenance["url_resolution"] = {"original_url": row["product_url"],
                                                "resolved_url": resolved, "method": "reviewed_redirect"}
                problems.remove("merchant_redirect_requires_resolution")
            if problems:
                raise ValueError("Cannot approve invalid candidate " + cid + ": " + ", ".join(problems))
            # A detail page on another host cannot establish this seller's variant/price.
            if urlsplit(approval["evidence_url"]).hostname != urlsplit(served_url).hostname:
                raise ValueError("Evidence must come from the candidate merchant")
            if timestamp(approval["reviewed_at"]) < row["observed_at"]:
                raise ValueError("Review cannot predate the observation")
            provenance["verification"] = approval
            offer_id = identity(approval["product_id"], row["retailer"].casefold(), row["product_url"],
                                row["observed_at"].isoformat(), row["currency"])
            record = {"offer_id": offer_id, "product_id": approval["product_id"], "retailer": row["retailer"],
                      "price": row["price"], "currency": row["currency"], "product_url": served_url,
                      "observed_at": row["observed_at"], "match_type": "exact",
                      "provenance": json.dumps(provenance, sort_keys=True)}
            if offer_id in silver and silver[offer_id]["price"] != record["price"]:
                raise ValueError("Conflicting prices for the same merchant observation")
            silver[offer_id] = record
    if set(approved) - used_approvals:
        raise ValueError("Approved candidates missing from raw input; include the complete raw archive")
    canonical = [{"product_id": p["product_id"], "title": p["title"], "brand": p["brand"],
                  "category": p["category"], "model": p["model"], "image_url": p.get("image_url"),
                  "attributes_json": json.dumps({k: p[k] for k in ("color", "size", "condition", "currency")})}
                 for p in products]
    return {"bronze": list(bronze.values()), "products": canonical, "offers": list(silver.values()),
            "review": list(review.values())}
