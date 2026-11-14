"""Generate an unapproved review queue, or validate saved approvals, without API calls."""
import argparse
import json
from pathlib import Path

from .common import load_envelopes, load_products
from .normalize import normalize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default="data/raw")
    parser.add_argument("--products", default="config/products.json")
    parser.add_argument("--approvals", default="config/approvals.json")
    parser.add_argument("--output", default="data/review_queue.json")
    args = parser.parse_args()
    result = normalize(load_envelopes(args.raw), load_products(args.products),
                       json.loads(Path(args.approvals).read_text()))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite prior review work. Explicitly choose a new output filename on reruns.
    with path.open("x") as stream:
        json.dump(result["review"], stream, indent=2)
        stream.write("\n")
    print(f"Candidates: {len(result['bronze'])}; approved offers: {len(result['offers'])}; queue: {path}")


if __name__ == "__main__":
    main()
