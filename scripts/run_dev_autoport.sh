#!/usr/bin/env bash
set -euo pipefail

export TOWN_ID="${TOWN_ID:-westford_ma}"
export TOWN_CONFIG_PATH="${TOWN_CONFIG_PATH:-$(pwd)/towns/${TOWN_ID}/town.yaml}"
export DB_PATH="${DB_PATH:-$(pwd)/data/generated/${TOWN_ID}.json}"

export FLASK_APP="town_collection_cal.service.app:create_app"
export FLASK_ENV="development"

PORT="$(
  python - <<'PY'
import socket
sock = socket.socket()
sock.bind(("", 0))
print(sock.getsockname()[1])
sock.close()
PY
)"

echo "Starting Flask dev server on port ${PORT}"
python -m flask run --host 0.0.0.0 --port "${PORT}"
