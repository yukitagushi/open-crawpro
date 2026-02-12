"""Resident live trading daemon (20s polling).

This is intended to run on a trusted host (e.g. the Mac mini running OpenClaw),
NOT on GitHub Actions.

Safety:
- Requires ENABLE_LIVE_TRADING=true to place orders.
- Enforces MARKET_ALLOWLIST, MAX_NOTIONAL_USD (per trade) and DAILY_NOTIONAL_CAP_USD.
- Uses FOK orders to avoid hanging open orders.

Current strategy (minimal v1):
- Poll orderbook top for the allowlisted market YES token.
- Store market_price_point time series.
- Read recent bullish content signals count as "context".
- If signals_last_30m>0 and spread is tight, place a $1 buy at best_ask (capped by MAX_PRICE).

TODO:
- Add RSI/MA/MACD computation and probabilistic exit planning.
- Add exit logic (sell) with timeouts.
"""

from __future__ import annotations

import os
import time
import json
import uuid
import logging
from datetime import datetime, timezone

from db_pg import connect, init_db
from infra import Infra, load_config_from_env
from gamma import extract_outcome_token_ids

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("live_daemon")


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


def _now() -> datetime:
    return datetime.now(timezone.utc)


def fetch_market(market_id: str) -> dict:
    import requests

    r = requests.get(f"https://gamma-api.polymarket.com/markets/{market_id}", timeout=20)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected Gamma /markets/{id} response")
    return data


def resolve_outcome_token_id(*, market_id: str, outcome_name: str) -> tuple[str, str]:
    """Resolve outcome token_id and question via Gamma /markets/{id}.

    outcome_name examples: "Yes", "No", "Up", "Down".
    """
    m = fetch_market(str(market_id))
    q = (m.get("question") or m.get("title") or "").strip() or "(no title)"

    mp = extract_outcome_token_ids(m)
    for k, v in mp.items():
        if k.strip().lower() == outcome_name.strip().lower():
            return str(v), q

    raise RuntimeError(f"Outcome token_id missing for outcome={outcome_name} (available={list(mp.keys())})")


def main() -> None:
    # Config
    poll_seconds = int(os.getenv("POLL_SECONDS") or "20")
    poll_seconds = max(5, min(poll_seconds, 300))

    enable_live = _env_bool("ENABLE_LIVE_TRADING", False)
    max_notional = _env_float("MAX_NOTIONAL_USD", 1.0)
    max_price = _env_float("MAX_PRICE", 0.99)
    daily_cap = _env_float("DAILY_NOTIONAL_CAP_USD", 20.0)
    min_signals_last_30m = int(os.getenv("MIN_SIGNALS_LAST_30M") or "0")

    allow = (os.getenv("MARKET_ALLOWLIST") or "").strip()
    if not allow:
        raise RuntimeError("MARKET_ALLOWLIST is required for live daemon")
    allow_market_id = allow.split(",")[0].strip()

    # MARKET_SLUG is optional for the daemon (we resolve via /markets/{id})
    slug = (os.getenv("MARKET_SLUG") or "").strip()

    # Connect DB + infra
    conn = connect()
    init_db(conn)

    cfg = load_config_from_env()
    infra = Infra(cfg)
    infra.connect()

    outcome_name = (os.getenv("OUTCOME_NAME") or "Up").strip() or "Up"
    token_id, question = resolve_outcome_token_id(market_id=allow_market_id, outcome_name=outcome_name)
    logger.info("Resolved market %s: %s (outcome=%s token=%s)", allow_market_id, question, outcome_name, token_id)

    last_trade_ts = 0.0
    loop_i = 0

    while True:
        loop_i += 1
        started = time.time()
        try:
            ob = infra.clob.get_order_book(token_id)
            bids = list(getattr(ob, "bids", None) or [])
            asks = list(getattr(ob, "asks", None) or [])

            best_bid = max((float(b.price) for b in bids), default=None)
            best_ask = min((float(a.price) for a in asks), default=None)
            mid = None
            if best_bid is not None and best_ask is not None:
                mid = (best_bid + best_ask) / 2.0

            # Persist price point
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO market_price_point(market_id, token_id, best_bid, best_ask, mid, snapshot_at, raw_json)
                    VALUES (%s,%s,%s,%s,%s, now(), %s::jsonb)
                    """,
                    (
                        str(allow_market_id),
                        str(token_id),
                        best_bid,
                        best_ask,
                        mid,
                        json.dumps({"bids": [getattr(b, "__dict__", {}) for b in bids[:3]], "asks": [getattr(a, "__dict__", {}) for a in asks[:3]]}),
                    ),
                )

                # Recent bullish signals (last 30m)
                cur.execute(
                    """
                    SELECT COUNT(*)::int
                    FROM content_signal
                    WHERE label='bullish'
                      AND created_at >= now() - interval '30 minutes'
                    """
                )
                signals_last_30m = int(cur.fetchone()[0] or 0)

                # Today's notional already submitted
                cur.execute(
                    """
                    SELECT COALESCE(SUM(price*size),0)::float8
                    FROM orders
                    WHERE status='submitted'
                      AND side='buy'
                      AND created_at >= date_trunc('day', now())
                      AND created_at <  date_trunc('day', now()) + interval '1 day'
                    """
                )
                todays_notional = float(cur.fetchone()[0] or 0.0)

            conn.commit()

            # Periodic status log
            if loop_i % 15 == 0:
                logger.info(
                    "tick market=%s outcome=%s bid=%s ask=%s mid=%s signals30m=%s todays_notional=%.2f enable_live=%s",
                    allow_market_id,
                    outcome_name,
                    best_bid,
                    best_ask,
                    mid,
                    signals_last_30m,
                    todays_notional,
                    enable_live,
                )

            # Simple entry gate (v1)
            if enable_live and best_ask is not None and signals_last_30m >= min_signals_last_30m:
                spread = None
                if best_bid is not None:
                    spread = best_ask - best_bid

                # Prevent ultra-frequent orders
                if time.time() - last_trade_ts < 60:
                    continue

                # Tight spread gate
                if spread is not None and spread > 0.05:
                    continue

                price = min(best_ask, max_price)
                if price <= 0:
                    continue
                size = max_notional / price
                # Polymarket amount precision can be strict; round to 2 decimals to be safe.
                size = round(size, 2)
                notional = price * size
                if todays_notional + notional > daily_cap:
                    continue

                client_order_id = f"live-{uuid.uuid4().hex[:10]}"
                evidence = {
                    "signals_last_30m": signals_last_30m,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "mid": mid,
                    "spread": spread,
                    "question": question,
                    "strategy": "v1_signals_and_tight_spread",
                }

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO orders(client_order_id, condition_id, token_id, side, price, size, status, raw_request_json)
                        VALUES (%s,%s,%s,'buy',%s,%s,'created',%s::jsonb)
                        """,
                        (client_order_id, str(allow_market_id), str(token_id), float(price), float(size), json.dumps(evidence)),
                    )

                    try:
                        from py_clob_client.clob_types import OrderArgs  # type: ignore

                        order_args = OrderArgs(token_id=str(token_id), price=float(price), size=float(size), side="BUY")
                        order = infra.clob.create_order(order_args)
                        resp = infra.clob.post_order(order, orderType="FOK", post_only=False)

                        order_id = None
                        if isinstance(resp, dict):
                            order_id = resp.get("orderID") or resp.get("orderId") or resp.get("id")

                        cur.execute(
                            "UPDATE orders SET status='submitted', order_id=%s, raw_response_json=%s::jsonb, updated_at=now() WHERE client_order_id=%s",
                            (str(order_id) if order_id else None, json.dumps(resp), client_order_id),
                        )
                        last_trade_ts = time.time()
                    except Exception as e:
                        cur.execute(
                            "UPDATE orders SET status='error', error=%s, updated_at=now() WHERE client_order_id=%s",
                            (str(e), client_order_id),
                        )
                    conn.commit()

        except Exception as e:
            logger.warning("loop error: %s", e)

        # Sleep
        elapsed = time.time() - started
        time.sleep(max(0.0, poll_seconds - elapsed))


if __name__ == "__main__":
    main()
