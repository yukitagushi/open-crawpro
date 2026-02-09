#!/usr/bin/env bash
set -euo pipefail

# Run Streamlit UI in background (local-only bind).
# Logs: logs/ui.log

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs

# Activate venv
source .venv311/bin/activate

# Install UI deps if missing
python -m pip install -r requirements-ui.txt >/dev/null

PORT="${PORT:-8501}"
HOST="${HOST:-127.0.0.1}"

# Kill existing streamlit on this port if any (best-effort)
python - <<'PY'
import os, signal, socket
port=int(os.getenv('PORT','8501'))
# naive: try connect; no reliable pid. leave as-is.
PY

nohup streamlit run ui_app.py \
  --server.headless true \
  --server.port "$PORT" \
  --server.address "$HOST" \
  --browser.gatherUsageStats false \
  > logs/ui.log 2>&1 &

echo $! > logs/ui.pid

echo "UI started: http://${HOST}:${PORT}"
echo "PID: $(cat logs/ui.pid)"
echo "Log: $ROOT_DIR/logs/ui.log"