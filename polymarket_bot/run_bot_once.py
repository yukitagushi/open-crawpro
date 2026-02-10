"""Single-run entrypoint for schedulers (GitHub Actions cron).

- Connects to infra
- Performs discovery
- Persists a bot_run row in Postgres

No trading is performed.
"""

from __future__ import annotations

import logging

from db_pg import connect, finish_run, init_db, start_run
from gamma import discover_markets
from infra import Infra, load_config_from_env


def _as_float(v):
    try:
        return float(v)
    except Exception:
        return None


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

        pairs = discover_markets(max_events=200)
        logger.info("discovered %d candidate markets", len(pairs))
        for p in pairs[:5]:
            logger.info("%s | yes=%s no=%s", p.question, p.yes_token_id, p.no_token_id)

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
