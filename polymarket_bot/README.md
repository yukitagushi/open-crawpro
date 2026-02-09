# Polymarket bot prototype (OpenClaw-ish layering)

## Status (important)
- We installed a user-land Python via **uv** (no sudo) and created `.venv311` (Python 3.11).
- `py-clob-client` installs successfully inside `.venv311`.
- Trading is **NOT implemented** yet; execution is a dry-run skeleton.

## Setup
```bash
cd polymarket_bot
# Use the Python 3.11 venv
source .venv311/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-ui.txt
```

## Run UI (recommended)
Local-only (no external exposure):
```bash
cd polymarket_bot
./scripts/run_ui.sh
# open http://127.0.0.1:8501
```
Stop:
```bash
./scripts/stop_ui.sh
```

## Env
Create `.env` (DO NOT commit it):
```env
PRIVATE_KEY=0x...
POLYGON_RPC_URL=https://polygon-rpc.com
CLOB_API_KEY=...
CLOB_API_SECRET=...
CLOB_API_PASSPHRASE=...
CLOB_HOST=https://clob.polymarket.com
CHAIN_ID=137
```

## Run quick checks (no secrets needed)
```bash
# Use the Python 3.11 venv
source .venv311/bin/activate
python -m py_compile infra.py
python infra.py  # will fail until env vars are set and py-clob-client is installable
```

## Scheduler mode (GitHub Actions)

This repo includes a cron workflow that runs every 5 minutes:
- `.github/workflows/polymarket-bot.yml`

### Cloud DB (Postgres)

For cron operation you should use Postgres (Neon/Supabase). Configure GitHub repo **Secrets**:
- `DATABASE_URL`

Schema is applied automatically at startup:
- `polymarket_bot/schema_postgres.sql`

### Entry points

- Local loop (SQLite): `python run_bot.py`
- Cron single-run (Postgres): `python run_bot_once.py`

> Safety: no trading is executed by default.
