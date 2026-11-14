#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://localhost:8000}"
curl -fsS "$BASE/health"; echo
curl -fsS "$BASE/products/search?q=headphones"; echo
curl -fsS "$BASE/products/demo-headphones-a/offers"; echo
curl -fsS "$BASE/products/demo-headphones-a/advice"; echo
