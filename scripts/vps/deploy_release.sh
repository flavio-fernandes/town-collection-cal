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

CONTAINER_NAME="${CONTAINER_NAME:-town-collection-cal}"
SERVICE_NAME="${SERVICE_NAME:-town-collection-cal.service}"
DB_UPDATE_SERVICE_NAME="${DB_UPDATE_SERVICE_NAME:-town-collection-cal-update.service}"
DB_UPDATE_TIMER_NAME="${DB_UPDATE_TIMER_NAME:-town-collection-cal-update.timer}"
PORT_MAP="${PORT_MAP:-8080:5000}"

HOST_TOWNS_DIR="${HOST_TOWNS_DIR:-/opt/town-collection-cal/towns}"
HOST_DATA_DIR="${HOST_DATA_DIR:-/opt/town-collection-cal/data}"

TOWN_ID="${TOWN_ID:-westford_ma}"
TOWN_CONFIG_PATH="${TOWN_CONFIG_PATH:-/app/towns/westford_ma/town.yaml}"
DB_PATH="${DB_PATH:-/app/data/generated/westford_ma.json}"
CACHE_DIR="${CACHE_DIR:-/app/data/cache}"
CORS_ALLOWED_ORIGINS="${CORS_ALLOWED_ORIGINS:-}"

if ! command -v docker >/dev/null 2>&1; then
  echo "error: docker is required" >&2
  exit 1
fi

echo "Pulling image: $IMAGE"
docker pull "$IMAGE"

echo "Building DB with image tag: $IMAGE_TAG"
"$(dirname "$0")/run_db_update.sh"

echo "Stopping systemd service: $SERVICE_NAME"
sudo systemctl stop "$SERVICE_NAME" || true

echo "Removing old container: $CONTAINER_NAME"
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "Creating container: $CONTAINER_NAME"
docker create \
  --name "$CONTAINER_NAME" \
  -p "$PORT_MAP" \
  -e TOWN_ID="$TOWN_ID" \
  -e TOWN_CONFIG_PATH="$TOWN_CONFIG_PATH" \
  -e DB_PATH="$DB_PATH" \
  -e CORS_ALLOWED_ORIGINS="$CORS_ALLOWED_ORIGINS" \
  -v "$HOST_TOWNS_DIR:/app/towns:ro" \
  -v "$HOST_DATA_DIR:/app/data" \
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
  "$IMAGE" >/dev/null

echo "Starting systemd service: $SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager --lines=10

if ! sudo systemctl list-unit-files --type=service --no-legend "$DB_UPDATE_SERVICE_NAME" | grep -q "^${DB_UPDATE_SERVICE_NAME}[[:space:]]"; then
  echo "error: required systemd unit not found: $DB_UPDATE_SERVICE_NAME" >&2
  exit 1
fi

if ! sudo systemctl list-unit-files --type=timer --no-legend "$DB_UPDATE_TIMER_NAME" | grep -q "^${DB_UPDATE_TIMER_NAME}[[:space:]]"; then
  echo "error: required systemd unit not found: $DB_UPDATE_TIMER_NAME" >&2
  exit 1
fi

echo "Reloading and restarting DB update timer: $DB_UPDATE_TIMER_NAME"
sudo systemctl daemon-reload
sudo systemctl restart "$DB_UPDATE_TIMER_NAME"
sudo systemctl status "$DB_UPDATE_TIMER_NAME" --no-pager --lines=10

echo "Done. Running image: $IMAGE"
