#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${STATE_DIR:-/var/lib/town-collection-cal}"
STATE_FILE="${STATE_FILE:-${STATE_DIR}/restart_count}"
CONTAINER_NAME="${CONTAINER_NAME:-town-collection-cal}"
BASE_DELAY_SECONDS="${BASE_DELAY_SECONDS:-60}"
MAX_DELAY_SECONDS="${MAX_DELAY_SECONDS:-900}"

mkdir -p "$STATE_DIR"

count=0
if [[ -f "$STATE_FILE" ]]; then
  read -r count < "$STATE_FILE" || count=0
fi

if ! [[ "$count" =~ ^[0-9]+$ ]]; then
  count=0
fi

delay=0
if (( count > 0 )); then
  delay=$BASE_DELAY_SECONDS
  for ((i = 1; i < count; i++)); do
    delay=$((delay * 2))
    if ((delay >= MAX_DELAY_SECONDS)); then
      delay=$MAX_DELAY_SECONDS
      break
    fi
  done
fi

if ((delay > 0)); then
  sleep "$delay"
fi

/usr/bin/docker start -a "$CONTAINER_NAME"
exit_code=$?

if [[ "$exit_code" -eq 0 ]]; then
  echo 0 > "$STATE_FILE"
else
  echo $((count + 1)) > "$STATE_FILE"
fi

exit "$exit_code"
