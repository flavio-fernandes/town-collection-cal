#!/usr/bin/env bash
set -euo pipefail

TOWN_ID="${TOWN_ID:-westford_ma}"
TOWN_CONFIG_PATH="${TOWN_CONFIG_PATH:-$(pwd)/towns/${TOWN_ID}/town.yaml}"
OUT_PATH="${OUT_PATH:-$(pwd)/data/generated/${TOWN_ID}.json}"
CACHE_DIR="${CACHE_DIR:-$(pwd)/data/cache}"

python -m town_collection_cal.updater build-db \
  --town "${TOWN_CONFIG_PATH}" \
  --out "${OUT_PATH}" \
  --cache-dir "${CACHE_DIR}"
