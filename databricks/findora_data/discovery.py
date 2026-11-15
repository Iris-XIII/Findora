"""Rank search candidates for inspection; title matches never constitute approval."""
import argparse
import json
import re
from pathlib import Path

from .common import load_envelopes, load_products
from .normalize import candidates


def contains(text, term):
    return bool(re.search(r"(?<![\w'’])" + re.escape(term.casefold()) + r"(?!\w)", text))


def assess(title, product):
    text = title.casefold()
    rules = product.get("discovery", {})
    terms = {
        "brand": [product["brand"]],
        "model": [product["model"], *rules.get("model_aliases", [])],
        "color": [product["color"]],
        "size": [product["size"], *rules.get("size_aliases", [])],
    }
    matched = [key for key, values in terms.items() if any(contains(text, v) for v in values)]
    conflicts = [term for term in rules.get("exclude_title_terms", []) if contains(text, term)]
    return {"title_matches": matched, "missing_title_attributes": [k for k in terms if k not in matched],
            "title_conflicts": conflicts,
            "score": sum({"brand": 2, "model": 5, "color": 3, "size": 3}[k] for k in matched),
            "status": "excluded_by_title" if conflicts else "needs_variant_review"}


def detail_tokens(rows, product):
    ranked = sorted(enumerate(rows), key=lambda pair: (-assess(pair[1].get("title", ""), product)["score"], pair[0]))
    seen = set()
    for _, row in ranked:
        token = row.get("immersive_product_page_token")
        if token and token not in seen and not assess(row.get("title", ""), product)["title_conflicts"]:
            seen.add(token)
            yield token


def shortlist(envelopes, products):
    targets = {p["product_id"]: p for p in products}
    result = {}
    for envelope in envelopes:
        product = targets.get(envelope.get("target_product_id"))
        if not product or envelope.get("source", "serpapi") != "serpapi":
            continue
        for row in candidates(envelope):
            result[row["candidate_id"]] = {
                "candidate_id": row["candidate_id"], "product_id": product["product_id"],
                "title": row["title"], "retailer": row["retailer"], "listed_price": row["price"],
                "currency": row["currency"], "product_url": row["product_url"],
                "observed_at": row["observed_at"].isoformat(), "source": "serpapi",
                "engine": envelope["request"]["engine"], "problems": row["problems"],
                **assess(row["title"], product), "approved": False,
                "still_requires": ["merchant variant and applicable price", "single item and new condition",
                                   "availability", "direct merchant destination"],
            }
    return sorted(result.values(), key=lambda r: (bool(r["title_conflicts"]), -r["score"], r["candidate_id"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default="data/raw")
    parser.add_argument("--products", default="config/focus_products.json")
    parser.add_argument("--output", default="data/serpapi_shortlist.json")
    args = parser.parse_args()
    rows = shortlist(load_envelopes(args.raw), load_products(args.products))
    output = Path(args.output)
    if output.resolve().is_relative_to(Path(args.raw).resolve()):
        raise ValueError("Write the shortlist outside raw input; it is not a source response")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, indent=2) + "\n")
    pending = [r for r in rows if not r["title_conflicts"]]
    print(f"SerpAPI candidates: {len(rows)}; pending review: {len(pending)}; excluded by title: {len(rows)-len(pending)}")
    for row in pending[:5]:
        print(f"{row['retailer']}: {row['title']} | {row['currency']} {row['listed_price']} | missing title fields: {', '.join(row['missing_title_attributes']) or 'none'}")
    print(f"Saved {output}; these are candidates, not approved recommendations.")


if __name__ == "__main__":
    main()
