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
Create `.env` (DO NOT commit it). We provide `.env.template`:
```bash
python env_template.py  # writes .env.template
cp .env.template .env
# then fill values
```

Required keys:
- PRIVATE_KEY
- POLYGON_RPC_URL
- CLOB_API_KEY
- CLOB_API_SECRET
- CLOB_API_PASSPHRASE

## Run quick checks (no secrets needed)
```bash
# Use the Python 3.11 venv
source .venv311/bin/activate
python -m py_compile infra.py
python infra.py  # will fail until env vars are set and py-clob-client is installable
```

## Local crawler daemon (Mac mini)

This mode crawls public RSS/blog sources **directly from the Mac mini** and stores them in Postgres.

Requirements:
- `DATABASE_URL` must be set in the environment (Actions secrets do NOT apply to local processes).

Start (background):
```bash
cd polymarket_bot
source .venv311/bin/activate
./scripts/run_crawler.sh
# logs: polymarket_bot/logs/crawler.log
```

Stop:
```bash
./scripts/stop_crawler.sh
```

Interval:
- `CRAWL_INTERVAL_SECONDS=60` (default)

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
