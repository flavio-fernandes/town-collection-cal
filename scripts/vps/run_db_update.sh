#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-/opt/town-collection-cal/.env.release}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "error: env file not found: $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

IMAGE_REPO="${IMAGE_REPO:-ghcr.io/flavio-fernandes/town-collection-cal}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE="${IMAGE_REPO}:${IMAGE_TAG}"

HOST_TOWNS_DIR="${HOST_TOWNS_DIR:-/opt/town-collection-cal/towns}"
HOST_DATA_DIR="${HOST_DATA_DIR:-/opt/town-collection-cal/data}"

TOWN_ID="${TOWN_ID:-westford_ma}"
TOWN_CONFIG_PATH="${TOWN_CONFIG_PATH:-/app/towns/westford_ma/town.yaml}"
OUT_PATH="${OUT_PATH:-/app/data/generated/westford_ma.json}"
CACHE_DIR="${CACHE_DIR:-/app/data/cache}"

UID_GID="${UID_GID:-$(id -u):$(id -g)}"

echo "Updating DB with image: $IMAGE"

docker run --rm \
  --user "$UID_GID" \
  -e TOWN_ID="$TOWN_ID" \
  -e TOWN_CONFIG_PATH="$TOWN_CONFIG_PATH" \
  -e OUT_PATH="$OUT_PATH" \
  -e CACHE_DIR="$CACHE_DIR" \
  -v "$HOST_TOWNS_DIR:/app/towns" \
  -v "$HOST_DATA_DIR:/app/data" \
  "$IMAGE" \
  python -m town_collection_cal.updater build-db \
    --town "$TOWN_CONFIG_PATH" \
    --out "$OUT_PATH" \
    --cache-dir "$CACHE_DIR"
