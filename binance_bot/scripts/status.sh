#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f daemon.pid ]; then
  pid=$(cat daemon.pid)
  if kill -0 "$pid" 2>/dev/null; then
    echo "running pid=$pid"
    ps -p "$pid" -o pid,etime,command
    exit 0
  fi
fi

echo "not running"
exit 1
