#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

IMAGE="${IMAGE:-ghcr.io/flavio-fernandes/town-collection-cal:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-town-collection-cal}"
PORT_HOST="${PORT_HOST:-8080}"
PORT_CONTAINER="${PORT_CONTAINER:-5000}"

TOWN_ID="${TOWN_ID:-westford_ma}"
TOWN_CONFIG_PATH="${TOWN_CONFIG_PATH:-${ROOT_DIR}/towns/${TOWN_ID}/town.yaml}"
DB_PATH="${DB_PATH:-${ROOT_DIR}/data/generated/${TOWN_ID}.json}"

if [[ ! -f "${DB_PATH}" ]]; then
  echo "Missing DB file: ${DB_PATH}"
  echo "Run scripts/update_db.sh (or the updater container) before starting the service."
  exit 1
fi

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

docker run -d --name "${CONTAINER_NAME}" \
  -p "${PORT_HOST}:${PORT_CONTAINER}" \
  -e TOWN_ID="${TOWN_ID}" \
  -e TOWN_CONFIG_PATH="/app/towns/${TOWN_ID}/town.yaml" \
  -e DB_PATH="/app/data/generated/${TOWN_ID}.json" \
  -v "${ROOT_DIR}/towns:/app/towns:ro" \
  -v "${ROOT_DIR}/data:/app/data" \
  --read-only \
  --tmpfs /tmp \
  --tmpfs /var/tmp \
  --cap-drop=ALL \
  --security-opt no-new-privileges:true \
  --pids-limit 200 \
  --memory 512m \
  --cpus 1 \
  --log-opt max-size=10m \
  --log-opt max-file=5 \
  "${IMAGE}"

echo "Started ${CONTAINER_NAME} on http://127.0.0.1:${PORT_HOST}"
