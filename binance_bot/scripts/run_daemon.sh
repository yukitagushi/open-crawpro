#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f daemon.pid ] && kill -0 "$(cat daemon.pid)" 2>/dev/null; then
  echo "binance daemon already running pid=$(cat daemon.pid)"
  exit 0
fi

source .venv/bin/activate

nohup python daemon.py > daemon.log 2>&1 &
echo $! > daemon.pid

echo "started pid=$!"
echo "log: $(pwd)/daemon.log"
