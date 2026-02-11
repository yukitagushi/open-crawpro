#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Stop by killing matching process.
PIDS=$(ps ax | grep "python .*run_crawler_loop.py" | grep -v grep | awk '{print $1}' || true)
if [ -z "$PIDS" ]; then
  echo "crawler not running"
  exit 0
fi

echo "stopping crawler: $PIDS"
kill $PIDS
