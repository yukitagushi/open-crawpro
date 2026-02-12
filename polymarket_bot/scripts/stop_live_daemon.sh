#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f live_daemon.pid ]; then
  echo "no pidfile"
  exit 0
fi

pid="$(cat live_daemon.pid)"
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  echo "stopped pid=$pid"
else
  echo "process not running (pid=$pid)"
fi

rm -f live_daemon.pid
