#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT_DIR/logs/ui.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No PID file: $PID_FILE"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "Stopped UI (pid=$PID)"
else
  echo "Process not running (pid=$PID)"
fi

rm -f "$PID_FILE"