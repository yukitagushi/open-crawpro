from __future__ import annotations

import json
import os
import time
import uuid
import logging
from decimal import Decimal, ROUND_DOWN

from dotenv import load_dotenv

from binance_api import BinanceApi
from db import connect, init_db
from strategy import decide_signal
from indicators import ema, rsi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("binance_daemon")


def _env_bool(name: str, default: bool = False) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "y", "on")


def _env_float(name: str, default: float) -> float:
    v = (os.getenv(name) or "").strip()
    if not v:
        return default
    try:
        return float(v)
    except Exception:
        return default


def _get_step_size(exchange_info: dict) -> tuple[Decimal, Decimal]:
    # returns (stepSize, tickSize)
    syms = exchange_info.get("symbols") or []
    if not syms:
        raise RuntimeError("exchangeInfo missing symbols")
    filters = syms[0].get("filters") or []
    step = None
    tick = None
    for f in filters:
        if f.get("filterType") == "LOT_SIZE":
            step = Decimal(str(f.get("stepSize")))
        if f.get("filterType") == "PRICE_FILTER":
            tick = Decimal(str(f.get("tickSize")))
    if step is None or tick is None:
        raise RuntimeError("could not find LOT_SIZE/PRICE_FILTER")
    return step, tick


def _quantize(value: Decimal, step: Decimal) -> Decimal:
    # round DOWN to step
    if step == 0:
        return value
    q = (value / step).to_integral_value(rounding=ROUND_DOWN) * step
    # strip exponent
    return q.quantize(step)


def blog_scores(conn) -> tuple[float, float]:
    # derive "MA" vs "RSI" preference from collected content signals tags
    # tags were implemented in polymarket_bot; we reuse those tables.
    ma = 0.0
    rs = 0.0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN tags @> ARRAY['移動平均'] THEN 1 ELSE 0 END),0)::float8 as ma,
                   COALESCE(SUM(CASE WHEN tags @> ARRAY['RSI'] THEN 1 ELSE 0 END),0)::float8 as rsi
            FROM content_signal
            WHERE created_at >= now() - interval '7 days'
              AND label='bullish'
            """
        )
        row = cur.fetchone() or (0.0, 0.0)
        ma = float(row[0] or 0.0)
        rs = float(row[1] or 0.0)
    return ma, rs


def main() -> None:
    load_dotenv(override=False)

    api_key = os.getenv("BINANCE_API_KEY") or ""
    api_secret = os.getenv("BINANCE_API_SECRET") or ""
    base_url = os.getenv("BINANCE_BASE_URL") or "https://api.binance.com"
    if not api_key or not api_secret:
        raise RuntimeError("BINANCE_API_KEY/SECRET required")

    enable = _env_bool("ENABLE_BINANCE_TRADING", False)
    max_per = Decimal(str(_env_float("MAX_QUOTE_PER_TRADE", 1.0))).quantize(Decimal("0.01"))
    daily_cap = Decimal(str(_env_float("DAILY_QUOTE_CAP", 5.0))).quantize(Decimal("0.01"))

    # Binance enforces per-symbol minimum notional (often $5). We'll respect it.
    min_notional_floor = Decimal(str(_env_float("MIN_NOTIONAL_FLOOR", 5.0))).quantize(Decimal("0.01"))

    symbols = [s.strip().upper() for s in (os.getenv("SYMBOLS") or "BTCUSDT,ETHUSDT").split(",") if s.strip()]
    interval = (os.getenv("INTERVAL") or "15m").strip()
    poll = int(os.getenv("POLL_SECONDS") or "20")

    ema_fast = int(os.getenv("EMA_FAST") or "9")
    ema_slow = int(os.getenv("EMA_SLOW") or "21")
    rsi_period = int(os.getenv("RSI_PERIOD") or "14")

    tp_pct = float(os.getenv("TAKE_PROFIT_PCT") or "0.006")
    sl_pct = float(os.getenv("STOP_LOSS_PCT") or "0.004")
    min_score = float(os.getenv("MIN_SIGNAL_SCORE") or "0.7")

    testnet_always_buy = _env_bool("TESTNET_ALWAYS_BUY", False)
    if testnet_always_buy and "testnet" not in base_url:
        raise RuntimeError("TESTNET_ALWAYS_BUY is only allowed when BINANCE_BASE_URL is a testnet endpoint")

    conn = connect()
    init_db(conn)

    api = BinanceApi(api_key, api_secret, base_url=base_url)

    # Preload symbol filters
    sym_filters: dict[str, tuple[Decimal, Decimal]] = {}
    for sym in symbols:
        info = api.exchange_info(sym)
        step, tick = _get_step_size(info)
        sym_filters[sym] = (step, tick)

    logger.info("binance daemon started symbols=%s interval=%s enable_trading=%s", symbols, interval, enable)

    last_trade_ts = 0.0
    last_balance_ts = 0.0

    while True:
        t0 = time.time()
        try:
            ma_score, rsi_score = blog_scores(conn)

            # Balance snapshot (rough USDT estimate) every ~60s
            if time.time() - last_balance_ts > 60:
                try:
                    acct = api.account()
                    bal = {b.get('asset'): {'free': b.get('free'), 'locked': b.get('locked')} for b in (acct.get('balances') or [])}
                    usdt = float(bal.get('USDT', {}).get('free') or 0) + float(bal.get('USDT', {}).get('locked') or 0)
                    # Use latest klines to estimate BTC/ETH value in USDT
                    btc_close = float(api.klines('BTCUSDT', interval, limit=1)[0][4])
                    eth_close = float(api.klines('ETHUSDT', interval, limit=1)[0][4])
                    btc_amt = float(bal.get('BTC', {}).get('free') or 0) + float(bal.get('BTC', {}).get('locked') or 0)
                    eth_amt = float(bal.get('ETH', {}).get('free') or 0) + float(bal.get('ETH', {}).get('locked') or 0)
                    total = usdt + btc_amt * btc_close + eth_amt * eth_close
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO binance_balance_snapshot(total_usdt_est, raw_json) VALUES (%s,%s::jsonb)",
                            (__import__('math').floor(total * 100) / 100.0, json.dumps({'usdt': usdt, 'btc': btc_amt, 'eth': eth_amt, 'btc_close': btc_close, 'eth_close': eth_close})),
                        )
                        conn.commit()
                    last_balance_ts = time.time()
                except Exception:
                    # ignore balance errors (still can compute indicators)
                    last_balance_ts = time.time()

            # naive daily cap check (DB)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COALESCE(SUM(quote_qty),0)::float8
                    FROM binance_order
                    WHERE created_at >= date_trunc('day', now())
                      AND created_at <  date_trunc('day', now()) + interval '1 day'
                      AND status='submitted'
                      AND side='BUY'
                    """
                )
                spent_today = Decimal(str(cur.fetchone()[0] or 0.0)).quantize(Decimal("0.01"))

            for sym in symbols:
                kl = api.klines(sym, interval, limit=200)
                closes = [float(k[4]) for k in kl]

                # compute indicators for logging
                from indicators import ema as _ema, rsi as _rsi

                ef = _ema(closes, ema_fast)
                es = _ema(closes, ema_slow)
                rv = _rsi(closes, rsi_period)

                # Always store indicator snapshot so we can inspect "trend" even when no trade happens.
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO binance_indicator_point(symbol, interval, close, ema_fast, ema_slow, rsi, blog_ma_score, blog_rsi_score, raw_json)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                        """,
                        (
                            sym,
                            interval,
                            float(closes[-1]),
                            float(ef) if ef is not None else None,
                            float(es) if es is not None else None,
                            float(rv) if rv is not None else None,
                            float(ma_score),
                            float(rsi_score),
                            json.dumps({"last_kline": kl[-1]}),
                        ),
                    )
                    conn.commit()

                sig = decide_signal(
                    closes,
                    ema_fast=ema_fast,
                    ema_slow=ema_slow,
                    rsi_period=rsi_period,
                    blog_ma_score=ma_score,
                    blog_rsi_score=rsi_score,
                    tp_pct=tp_pct,
                    sl_pct=sl_pct,
                    min_score=min_score,
                    always_buy=(testnet_always_buy and enable),
                )
                if not sig:
                    continue

                # cooldown
                if time.time() - last_trade_ts < 60:
                    continue

                last_price = Decimal(str(closes[-1]))
                step, tick = sym_filters[sym]

                # Determine quote amount respecting exchange minimum notional
                quote_to_use = max_per
                if quote_to_use < min_notional_floor:
                    quote_to_use = min_notional_floor

                if spent_today + quote_to_use > daily_cap:
                    continue

                # Submit BUY
                run_id = str(uuid.uuid4())

                evidence = {
                    "signal": sig.__dict__,
                    "blog_ma": ma_score,
                    "blog_rsi": rsi_score,
                    "last_close": float(last_price),
                    "quote_to_use": float(quote_to_use),
                }

                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO binance_signal(symbol, kind, score, evidence_json) VALUES (%s,%s,%s,%s::jsonb)",
                        (sym, sig.kind, float(sig.score), json.dumps(evidence)),
                    )
                    conn.commit()

                if not enable:
                    continue

                client_tag = f"auto-{run_id[:8]}"
                req = {"symbol": sym, "quote": float(max_per), "tag": client_tag, **evidence}

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO binance_order(symbol, side, status, quote_qty, raw_request_json)
                        VALUES (%s,'BUY','created',%s,%s::jsonb)
                        RETURNING id
                        """,
                        (sym, float(quote_to_use), json.dumps(req)),
                    )
                    oid_row = cur.fetchone()
                    order_row_id = oid_row[0]
                    conn.commit()

                try:
                    resp = api.new_order_market_buy_quote(sym, float(quote_to_use))
                    # derive filled base qty & avg price
                    fills = resp.get("fills") or []
                    base_qty = Decimal("0")
                    quote_spent = Decimal("0")
                    for f in fills:
                        base_qty += Decimal(str(f.get("qty")))
                        quote_spent += Decimal(str(f.get("qty"))) * Decimal(str(f.get("price")))
                    if base_qty <= 0:
                        base_qty = Decimal(str(resp.get("executedQty") or "0"))
                    avg_price = (quote_spent / base_qty) if (base_qty and quote_spent) else last_price

                    # OCO sell
                    tp_price = _quantize(avg_price * (Decimal("1") + Decimal(str(sig.target_pct))), tick)
                    sl_price = _quantize(avg_price * (Decimal("1") - Decimal(str(sig.stop_pct))), tick)
                    sl_limit = _quantize(sl_price * Decimal("0.999"), tick)

                    qty = _quantize(base_qty, step)
                    if qty <= 0:
                        raise RuntimeError("computed qty <= 0")

                    # Binance requires strings with correct precision
                    def fmt_dec(d: Decimal) -> str:
                        s = format(d, 'f')
                        # strip trailing zeros
                        if '.' in s:
                            s = s.rstrip('0').rstrip('.')
                        return s

                    oco = api.new_oco_sell(
                        sym,
                        quantity=fmt_dec(qty),
                        price=fmt_dec(tp_price),
                        stop_price=fmt_dec(sl_price),
                        stop_limit_price=fmt_dec(sl_limit),
                    )

                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE binance_order
                            SET status='submitted',
                                order_id=%s,
                                base_qty=%s,
                                price=%s,
                                take_profit_price=%s,
                                stop_loss_price=%s,
                                stop_limit_price=%s,
                                oco_order_list_id=%s,
                                raw_response_json=%s::jsonb
                            WHERE id=%s
                            """,
                            (
                                str(resp.get("orderId")),
                                float(qty),
                                float(avg_price),
                                float(tp_price),
                                float(sl_price),
                                float(sl_limit),
                                str(oco.get("orderListId")) if isinstance(oco, dict) and oco.get("orderListId") is not None else None,
                                json.dumps({"buy": resp, "oco": oco}),
                                order_row_id,
                            ),
                        )
                        conn.commit()

                    last_trade_ts = time.time()

                except Exception as e:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE binance_order SET status='error', error=%s WHERE id=%s",
                            (str(e), order_row_id),
                        )
                        conn.commit()

        except Exception as e:
            logger.warning("loop error: %s", e)

        dt = time.time() - t0
        time.sleep(max(1, poll - dt))


if __name__ == "__main__":
    main()
