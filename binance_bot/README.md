# Binance Auto Trader (BTC/ETH, 15m)

Resident daemon intended to run on the Mac mini (or VPS) for sub-minute polling.

## Safety
- Withdrawal permission MUST be disabled on the Binance API key.
- Trading is disabled unless `ENABLE_BINANCE_TRADING=true`.
- Enforces per-trade and daily notional caps.

## Run
```bash
cd binance_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env
# fill .env
python daemon.py
```

## Stop
Ctrl+C

## Env
See `.env.template`.
