#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f live_daemon.pid ] && kill -0 "$(cat live_daemon.pid)" 2>/dev/null; then
  echo "live_daemon already running (pid=$(cat live_daemon.pid))"
  exit 0
fi

# Load .env if present
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# Activate venv (created locally)
if [ -f .venv311/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv311/bin/activate
fi

# Defaults
: "${POLL_SECONDS:=20}"

nohup python live_daemon.py > logs/live_daemon.log 2>&1 &
echo $! > live_daemon.pid

echo "started live_daemon pid=$! (POLL_SECONDS=$POLL_SECONDS)"
echo "log: $(pwd)/logs/live_daemon.log"
