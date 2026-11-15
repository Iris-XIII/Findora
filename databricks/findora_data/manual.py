"""Import an evidenced manual observation; exact-match approval remains a separate step."""
import argparse
import json
import math
from pathlib import Path

from .common import identity, merchant_url, timestamp, utc_now


def manual_candidates(envelope):
    observation = envelope["observation"]
    observed = timestamp(observation.get("observed_at"))
    recorded = timestamp(envelope.get("recorded_at"))
    if observed > recorded:
        raise ValueError("Manual observation cannot be later than its recording time")
    for key in ("title", "retailer", "source_product_id", "evidence_ref", "evidence_notes"):
        if not isinstance(observation.get(key), str) or not observation[key].strip():
            raise ValueError("Manual observation requires " + key)
    url = observation.get("product_url")
    if not merchant_url(url):
        raise ValueError("Manual observation requires a direct merchant URL")
    price = observation.get("price")
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
        raise ValueError("Manual price must be a positive finite number")
    if observation.get("currency") != "USD":
        raise ValueError("Manual MVP observations must be USD")
    cid = identity("manual_snapshot", observation["retailer"].casefold(), url,
                   observation["source_product_id"], observed.isoformat(), float(price))
    provenance = {"source": "manual_snapshot", "source_type": "snapshot", "candidate_id": cid,
                  "target_product_id": envelope["target_product_id"],
                  "source_observed_at": observed.isoformat(), "recorded_at": recorded.isoformat(),
                  "evidence_ref": observation["evidence_ref"], "evidence_notes": observation["evidence_notes"],
                  "observation_precision": observation.get("observation_precision", "unspecified"),
                  "reported_attributes": observation.get("reported_attributes", {})}
    return [{"candidate_id": cid, "target_product_id": envelope["target_product_id"],
             "source_product_id": observation["source_product_id"], "title": observation["title"],
             "retailer": observation["retailer"], "price": float(price), "currency": "USD",
             "product_url": url, "observed_at": observed, "batch_id": "manual-" + cid,
             "provenance": provenance, "problems": []}]


def make_envelope(observation, target_product_id, recorded_at=None):
    envelope = {"format_version": 1, "source": "manual_snapshot", "source_type": "snapshot",
                "target_product_id": target_product_id, "recorded_at": recorded_at or utc_now(),
                "observation": observation}
    manual_candidates(envelope)
    return envelope


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON with target_product_id and observation")
    parser.add_argument("--output", default="data/raw")
    args = parser.parse_args()
    draft = json.loads(Path(args.input).read_text())
    envelope = make_envelope(draft["observation"], draft["target_product_id"])
    cid = manual_candidates(envelope)[0]["candidate_id"]
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"manual_{cid}.json"
    if path.exists():
        existing = json.loads(path.read_text())
        if existing["observation"] != envelope["observation"] or existing["target_product_id"] != envelope["target_product_id"]:
            raise ValueError("Conflicting manual observation; existing evidence was not overwritten")
        print(f"Existing observation preserved: {path}")
    else:
        with path.open("x") as stream:
            json.dump(envelope, stream, indent=2)
            stream.write("\n")
        print(f"Saved unapproved manual observation: {path}")


if __name__ == "__main__":
    main()
