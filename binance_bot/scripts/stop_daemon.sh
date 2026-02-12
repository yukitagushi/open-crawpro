#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f daemon.pid ]; then
  echo "no pidfile"
  exit 0
fi

pid="$(cat daemon.pid)"
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  echo "stopped pid=$pid"
else
  echo "process not running pid=$pid"
fi

rm -f daemon.pid
