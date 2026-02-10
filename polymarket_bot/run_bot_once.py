"""Single-run entrypoint for schedulers (GitHub Actions cron).

- Connects to infra
- Performs discovery
- Persists a bot_run row in Postgres

No trading is performed.
"""

from __future__ import annotations

import logging
import os
import uuid

from db_pg import connect, finish_run, init_db, start_run
from gamma import discover_markets
from infra import Infra, load_config_from_env


def _as_float(v):
    try:
        return float(v)
    except Exception:
        return None


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if not v:
        return default
    try:
        return float(v)
    except Exception:
        return default


def _guess_ts(trade: dict):
    # Try common timestamp fields; if none, return None
    for k in ("timestamp", "created_at", "createdAt", "time", "ts"):
        if k in trade and trade[k] is not None:
            return trade[k]
    return None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_bot_once")


def main() -> None:
    conn = connect()
    init_db(conn)

    run = start_run(conn)
    try:
        cfg = load_config_from_env()
        infra = Infra(cfg)
        infra.connect()

        # Discovery filters (default: broad so we always find something)
        want_15min = _env_bool("DISCOVERY_15MIN", False)
        want_crypto = _env_bool("DISCOVERY_CRYPTO_TAG", False)
        require_open = _env_bool("DISCOVERY_REQUIRE_OPEN", True)
        require_liq = _env_bool("DISCOVERY_REQUIRE_LIQUIDITY", True)

        pairs = discover_markets(
            want_15min=want_15min,
            want_crypto_tag=want_crypto,
            require_open=require_open,
            require_liquidity=require_liq,
            max_events=800,
        )
        logger.info(
            "discovered %d candidate markets (filters: 15min=%s crypto=%s open=%s liq=%s)",
            len(pairs),
            want_15min,
            want_crypto,
            require_open,
            require_liq,
        )
        for p in pairs[:5]:
            logger.info("%s | yes=%s no=%s", p.question, p.yes_token_id, p.no_token_id)

        # ---- Minimal trade plan (DRY_RUN first) ----
        DRY_RUN = _env_bool("DRY_RUN", True)
        MAX_NOTIONAL_USD = _env_float("MAX_NOTIONAL_USD", 1.0)
        MAX_PRICE = _env_float("MAX_PRICE", 0.55)

        chosen = pairs[0] if pairs else None
        plan = None
        if chosen is not None and infra.clob is not None:
            try:
                ob = infra.clob.get_order_book(chosen.yes_token_id)
                best_ask = _as_float(ob.asks[0].price) if getattr(ob, "asks", None) else None
                if best_ask is not None:
                    price = min(best_ask, MAX_PRICE)
                    size = MAX_NOTIONAL_USD / max(price, 1e-9)
                    plan = {
                        "market_id": chosen.market_id,
                        "question": chosen.question,
                        "token_id": chosen.yes_token_id,
                        "side": "buy",
                        "best_ask": best_ask,
                        "limit_price": price,
                        "size": size,
                        "dry_run": DRY_RUN,
                    }
            except Exception as e:
                logger.warning("orderbook/plan failed: %s", e)

        # Persist what we saw (for UI/analytics)
        with conn.cursor() as cur:
            for p in pairs:
                cur.execute(
                    """
                    INSERT INTO discovered_market(market_id, question, yes_token_id, no_token_id)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (market_id)
                    DO UPDATE SET
                      question = EXCLUDED.question,
                      yes_token_id = EXCLUDED.yes_token_id,
                      no_token_id = EXCLUDED.no_token_id,
                      last_seen_at = now(),
                      seen_count = discovered_market.seen_count + 1
                    """,
                    (p.market_id, p.question, p.yes_token_id, p.no_token_id),
                )

            # Save planned order (dry-run) to orders table
            if plan is not None:
                client_order_id = f"plan-{run.run_id}-{uuid.uuid4().hex[:8]}"
                cur.execute(
                    """
                    INSERT INTO orders(client_order_id, condition_id, token_id, side, price, size, status, raw_request_json)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    """,
                    (
                        client_order_id,
                        plan["market_id"],
                        plan["token_id"],
                        plan["side"],
                        float(plan["limit_price"]),
                        float(plan["size"]),
                        "dry_run" if DRY_RUN else "submitted",
                        __import__("json").dumps(plan),
                    ),
                )

            # Fetch user trades (used as fills) and store them.
            # NOTE: TradeParams currently supports maker_address filter.
            from py_clob_client.clob_types import TradeParams  # type: ignore

            # Try a few variants to avoid missing fills due to filtering differences.
            trades = []
            try:
                trades = infra.clob.get_trades(TradeParams(maker_address=infra.address))
            except Exception:
                trades = []

            if not trades:
                try:
                    trades = infra.clob.get_trades(TradeParams())
                except Exception:
                    trades = []

            inserted = 0
            for t in trades:
                if not isinstance(t, dict):
                    continue
                fill_id = t.get("id") or t.get("trade_id") or t.get("fill_id")
                if not fill_id:
                    # as a last resort, derive a stable hash-ish id
                    fill_id = __import__("hashlib").sha256(__import__("json").dumps(t, sort_keys=True).encode("utf-8")).hexdigest()

                price = _as_float(t.get("price"))
                size = _as_float(t.get("size") or t.get("quantity"))
                side = (t.get("side") or t.get("taker_side") or t.get("maker_side") or "").lower() or "unknown"

                # Best-effort mapping
                order_id = t.get("order_id") or t.get("orderId")
                condition_id = t.get("market") or t.get("condition_id") or t.get("conditionId")
                token_id = t.get("asset_id") or t.get("token_id") or t.get("tokenId")
                fee = _as_float(t.get("fee"))

                if price is None or size is None:
                    continue

                cur.execute(
                    """
                    INSERT INTO fills(fill_id, order_id, condition_id, token_id, side, price, size, fee, raw_json)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (fill_id) DO NOTHING
                    """,
                    (
                        str(fill_id),
                        str(order_id) if order_id is not None else None,
                        str(condition_id) if condition_id is not None else None,
                        str(token_id) if token_id is not None else None,
                        side,
                        float(price),
                        float(size),
                        float(fee) if fee is not None else None,
                        __import__("json").dumps(t),
                    ),
                )
                inserted += cur.rowcount

            cur.execute(
                "UPDATE bot_run SET discovered_count=%s, trades_fetched=%s, fills_inserted=%s WHERE run_id=%s",
                (len(pairs), len(trades), inserted, run.run_id),
            )

        conn.commit()

        finish_run(conn, run, status="ok")

    except Exception as e:
        logger.exception("run error: %s", e)
        finish_run(conn, run, status="error", error=str(e))
        raise


if __name__ == "__main__":
    main()
