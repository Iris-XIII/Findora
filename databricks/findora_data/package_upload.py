"""Build a credential-free ZIP for direct workspace import; never calls an API."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from .common import load_envelopes, load_products
from .normalize import normalize


def copy_snapshots(source, destination):
    """Copy immutable raw files; preflight conflicts before making any changes."""
    source, destination = Path(source), Path(destination)
    files = sorted(source.glob("*.json"))
    if not files:
        raise ValueError("No packaged snapshots found")
    for path in files:
        target = destination / path.name
        if target.exists() and target.read_bytes() != path.read_bytes():
            raise ValueError(f"Snapshot filename conflict: {path.name}; existing history was not overwritten")
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in files:
        target = destination / path.name
        if not target.exists():
            target.write_bytes(path.read_bytes())
            copied += 1
    return copied


def reject_credentials(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in {"api_key", "authorization", "access_token", "client_secret"} and item not in (None, "", "[REDACTED]"):
                raise ValueError("Credential-like field in JSON input; refusing to package")
            reject_credentials(item)
    elif isinstance(value, list):
        for item in value:
            reject_credentials(item)
    elif isinstance(value, str):
        if re.search(r"(?i)api_key=(?!\[REDACTED\]|%5BREDACTED%5D)[^&\s]+", value):
            raise ValueError("Unredacted API-key URL in JSON input; refusing to package")


def build_package(root, output):
    root, output = Path(root), Path(output)
    products = load_products(root / "config/products.json")
    approvals = json.loads((root / "config/approvals.json").read_text())
    raw = load_envelopes(root / "data/raw")
    for value in (products, approvals, *raw):
        reject_credentials(value)
    result = normalize(raw, products, approvals)
    # Explicit allowlist: never zip an entire workspace or include private .env/data files by accident.
    files = {"01_ingest.py": root / "notebooks/01_ingest.py",
             "START_HERE.md": root / "UPLOAD.md"}
    for directory, pattern in (("findora_data", "*.py"), ("config", "*.json"), ("sql", "*.sql")):
        for path in (root / directory).glob(pattern):
            if directory == "config" and path.name not in {"products.json", "approvals.json"}:
                continue
            files[f"{directory}/{path.name}"] = path
    for name in ("app.py", "app.yaml", "requirements.txt"):
        files[f"app/{name}"] = root / "app" / name
    for path in sorted((root / "data/raw").glob("*.json")):
        files[f"snapshots/{path.name}"] = path
    manifest = {"raw_file_count": len(raw), "expected_bronze_candidates": len(result["bronze"]),
                "expected_canonical_products": len(result["products"]),
                "expected_approved_offers": len(result["offers"]),
                "files_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, "Findora_B/" + name)
        archive.writestr("Findora_B/PACKAGE_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--output", default="data/upload/findora_databricks_upload.zip")
    args = parser.parse_args()
    manifest = build_package(args.root, args.output)
    print(json.dumps({k: v for k, v in manifest.items() if k != "files_sha256"}, indent=2))
    print(f"Upload package: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
