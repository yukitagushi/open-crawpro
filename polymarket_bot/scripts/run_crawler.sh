#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p logs

# Run crawler loop in background.
# Requires DATABASE_URL in the environment.
nohup python run_crawler_loop.py > logs/crawler.log 2>&1 &

echo "crawler started (pid=$!). log: logs/crawler.log"
