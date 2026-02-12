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
from gamma import TokenPair, discover_markets, extract_yes_no_token_ids, fetch_events
from infra import Infra, load_config_from_env
from content_ingest import ingest_default_feeds
from signal import score_text
from tagger import extract_tags


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
        # Gamma liquidity fields can be missing/unstable; default to False so discovery doesn't go empty.
        require_liq = _env_bool("DISCOVERY_REQUIRE_LIQUIDITY", False)

        pairs = discover_markets(
            want_15min=want_15min,
            want_crypto_tag=want_crypto,
            require_open=require_open,
            require_liquidity=require_liq,
            max_events=800,
        )

        # ---- Content ingest (RSS/blog) ----
        content_items_inserted, content_injection_flagged = (0, 0)
        signals_inserted = 0
        ingest_started_at = __import__("datetime").datetime.utcnow()
        try:
            content_items_inserted, content_injection_flagged = ingest_default_feeds(conn)
            conn.commit()

            # Phase A signal extraction (keyword-based)
            new_signal_rows = []
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT source_key, item_id, title, summary, content_text, url
                    FROM content_item
                    WHERE fetched_at >= %s
                    ORDER BY fetched_at DESC
                    LIMIT 400
                    """,
                    (ingest_started_at,),
                )
                rows = cur.fetchall() or []

                for source_key, item_id, title, summary, content_text, url in rows:
                    s = score_text(title, summary, content_text)

                    # Tag the content item itself (best-effort)
                    tags = extract_tags(title, summary, content_text)
                    try:
                        cur.execute(
                            "UPDATE content_item SET tags=%s WHERE source_key=%s AND item_id=%s",
                            (tags, str(source_key), str(item_id)),
                        )
                    except Exception:
                        pass

                    # Only record strong bullish signals for now
                    if s.label != "bullish" or s.score < 2:
                        continue
                    rationale = {
                        "hits_bull": s.hits_bull,
                        "hits_bear": s.hits_bear,
                        "score": s.score,
                        "label": s.label,
                        "tags": tags,
                    }
                    cur.execute(
                        """
                        INSERT INTO content_signal(source_key, item_id, score, label, tags, rationale_json)
                        VALUES (%s,%s,%s,%s,%s,%s::jsonb)
                        ON CONFLICT (source_key, item_id) DO NOTHING
                        """,
                        (str(source_key), str(item_id), int(s.score), str(s.label), tags, __import__("json").dumps(rationale)),
                    )
                    if cur.rowcount:
                        signals_inserted += 1
                        new_signal_rows.append(
                            {
                                "source": str(source_key),
                                "item_id": str(item_id),
                                "score": int(s.score),
                                "title": (title or "")[:140],
                                "url": url or "",
                            }
                        )
            conn.commit()

            # Snapshot market data at signal time (Phase 2: validate)
            signal_snapshots_inserted = 0
            try:
                if infra.clob is not None and new_signal_rows and plans:
                    # Use the allowlisted market's YES token_id (from plans[0]) for now.
                    # (We can expand to mapping later.)
                    market_id = str(plans[0].get("market_id") or "")
                    token_id = str(plans[0].get("token_id") or "")
                    if market_id and token_id:
                        ob = infra.clob.get_order_book(token_id)
                        best_bid = _as_float(ob.bids[0].price) if getattr(ob, "bids", None) else None
                        best_ask = _as_float(ob.asks[0].price) if getattr(ob, "asks", None) else None
                        mid = None
                        if best_bid is not None and best_ask is not None:
                            mid = (float(best_bid) + float(best_ask)) / 2.0
                        raw = {
                            "market_id": market_id,
                            "token_id": token_id,
                            "best_bid": best_bid,
                            "best_ask": best_ask,
                            "mid": mid,
                        }
                        with conn.cursor() as cur:
                            for r in new_signal_rows:
                                cur.execute(
                                    """
                                    INSERT INTO signal_market_snapshot(source_key, item_id, market_id, token_id, best_bid, best_ask, mid, raw_json)
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                                    ON CONFLICT (source_key, item_id, market_id, token_id) DO NOTHING
                                    """,
                                    (
                                        r["source"],
                                        r["item_id"],
                                        market_id,
                                        token_id,
                                        float(best_bid) if best_bid is not None else None,
                                        float(best_ask) if best_ask is not None else None,
                                        float(mid) if mid is not None else None,
                                        __import__("json").dumps(raw),
                                    ),
                                )
                                signal_snapshots_inserted += cur.rowcount
                        conn.commit()
            except Exception as e:
                logger.warning("signal snapshot failed: %s", e)

            # Notify Slack (optional) if new bullish signals were inserted
            webhook = (os.getenv("SLACK_WEBHOOK_URL") or "").strip()
            if webhook and signals_inserted > 0:
                try:
                    import requests  # already in requirements

                    top = sorted(new_signal_rows, key=lambda x: x["score"], reverse=True)[:5]
                    lines = [f"・[{t['score']}] {t['title']} {t['url']}".strip() for t in top]
                    text = "強気シグナルを検出（新規 {n}件）\n".format(n=signals_inserted) + "\n".join(lines)
                    requests.post(webhook, json={"text": text}, timeout=10).raise_for_status()
                except Exception as e:
                    logger.warning("slack webhook notify failed: %s", e)
        except Exception as e:
            logger.warning("content ingest failed: %s", e)
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

        # Live trading requires an explicit opt-in switch
        ENABLE_LIVE_TRADING = _env_bool("ENABLE_LIVE_TRADING", False)
        DAILY_NOTIONAL_CAP_USD = _env_float("DAILY_NOTIONAL_CAP_USD", 20.0)

        # Optionally pin to a allowlist of condition_id/market_id (comma-separated)
        allowlist_raw = (os.getenv("MARKET_ALLOWLIST") or "").strip()
        allow = {x.strip() for x in allowlist_raw.split(",") if x.strip()} if allowlist_raw else set()
        if allow:
            pairs = [p for p in pairs if (p.market_id in allow)]

            # If discovery didn't surface the pinned market (pagination), try fetching it directly via Gamma slug.
            if not pairs:
                slug = (os.getenv("MARKET_SLUG") or "").strip()
                if slug:
                    try:
                        evs = fetch_events(limit=1, offset=0, params={"slug": slug})
                        if evs and isinstance(evs[0], dict):
                            ev = evs[0]
                            markets = ev.get("markets") or []
                            for m in markets:
                                if not isinstance(m, dict):
                                    continue
                                mid = str(m.get("id") or m.get("market_id") or m.get("conditionId") or "")
                                if mid not in allow:
                                    continue
                                yes, no = extract_yes_no_token_ids(m)
                                if not yes or not no:
                                    continue
                                q = (ev.get("title") or ev.get("question") or "").strip() or "(no title)"
                                pairs.append(
                                    TokenPair(
                                        market_id=mid,
                                        question=q,
                                        yes_token_id=str(yes),
                                        no_token_id=str(no),
                                    )
                                )
                    except Exception as e:
                        logger.warning("gamma slug fetch failed: %s", e)

        # How many markets to generate paper plans for
        N_MARKETS_PER_RUN = int(os.getenv("N_MARKETS_PER_RUN") or "1")
        N_MARKETS_PER_RUN = max(1, min(N_MARKETS_PER_RUN, 50))

        plans = []
        if infra.clob is not None:
            for chosen in pairs[:N_MARKETS_PER_RUN]:
                try:
                    ob = infra.clob.get_order_book(chosen.yes_token_id)
                    best_ask = _as_float(ob.asks[0].price) if getattr(ob, "asks", None) else None
                    if best_ask is None:
                        continue
                    price = min(best_ask, MAX_PRICE)
                    price = float(f"{price:.3f}")

                    from decimal import Decimal, ROUND_DOWN

                    notional_target = Decimal(str(round(MAX_NOTIONAL_USD, 2)))
                    p = Decimal(str(price))
                    if p <= 0:
                        continue
                    size_d = (notional_target / p).to_integral_value(rounding=ROUND_DOWN)
                    if size_d <= 0:
                        continue
                    size = float(size_d)
                    plans.append(
                        {
                            "market_id": chosen.market_id,
                            "question": chosen.question,
                            "token_id": chosen.yes_token_id,
                            "side": "buy",
                            "best_ask": best_ask,
                            "limit_price": price,
                            "size": size,
                            "dry_run": DRY_RUN,
                        }
                    )
                except Exception as e:
                    logger.warning("orderbook/plan failed (%s): %s", getattr(chosen, "market_id", "?"), e)

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

            # Save planned order(s) (dry-run) to orders table
            paper_fills_inserted = 0
            live_orders_submitted = 0
            live_orders_blocked = 0

            # Pre-compute today's notional spent (safety cap)
            todays_notional = 0.0
            try:
                with conn.cursor() as cur2:
                    cur2.execute(
                        """
                        SELECT COALESCE(SUM(price*size),0)::float8
                        FROM orders
                        WHERE status='submitted'
                          AND side='buy'
                          AND created_at >= date_trunc('day', now())
                          AND created_at <  date_trunc('day', now()) + interval '1 day'
                        """
                    )
                    todays_notional = float(cur2.fetchone()[0] or 0.0)
            except Exception:
                todays_notional = 0.0

            for plan in plans:
                client_order_id = f"plan-{run.run_id}-{uuid.uuid4().hex[:8]}"
                # Attach minimal evidence from content signals (last 30 minutes)
                evidence = {"signals_last_30m": 0, "top_tags": []}
                try:
                    with conn.cursor() as cur3:
                        cur3.execute(
                            """
                            SELECT COUNT(*)::int
                            FROM content_signal
                            WHERE label='bullish'
                              AND created_at >= now() - interval '30 minutes'
                            """
                        )
                        evidence["signals_last_30m"] = int(cur3.fetchone()[0] or 0)

                        cur3.execute(
                            """
                            SELECT tag, COUNT(*)::int as cnt
                            FROM (
                              SELECT unnest(COALESCE(tags, ARRAY[]::text[])) as tag
                              FROM content_signal
                              WHERE label='bullish'
                                AND created_at >= now() - interval '24 hours'
                            ) t
                            GROUP BY tag
                            ORDER BY cnt DESC
                            LIMIT 5
                            """
                        )
                        evidence["top_tags"] = [r[0] for r in (cur3.fetchall() or []) if r and r[0]]
                except Exception:
                    pass

                req_json = {**plan, "evidence": evidence}

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
                        __import__("json").dumps(req_json),
                    ),
                )

                # ---- Paper-trade simulation (Phase B) ----
                # For data collection, we do a simple "mark fill":
                # - if we can read best_ask and the side is buy, record a paper fill at best_ask.
                # This guarantees we accumulate paper fills for analysis, without sending any real orders.
                if DRY_RUN and plan.get("best_ask") is not None:
                    try:
                        best_ask = float(plan["best_ask"])
                        size = float(plan["size"])
                        if plan.get("side") == "buy":
                            paper_fill_id = f"paper-{client_order_id}"  # stable
                            paper = {
                                **plan,
                                "paper_fill_id": paper_fill_id,
                                "fill_price": best_ask,
                                "fill_size": size,
                                "fill_rule": "mark_fill_best_ask",
                            }
                            cur.execute(
                                """
                                INSERT INTO paper_fills(paper_fill_id, client_order_id, condition_id, token_id, side, price, size, raw_json)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                                ON CONFLICT (paper_fill_id) DO NOTHING
                                """,
                                (
                                    paper_fill_id,
                                    client_order_id,
                                    plan["market_id"],
                                    plan["token_id"],
                                    plan["side"],
                                    float(best_ask),
                                    float(size),
                                    __import__("json").dumps(paper),
                                ),
                            )
                            paper_fills_inserted += cur.rowcount
                    except Exception as e:
                        logger.warning("paper-trade simulation failed: %s", e)

                # ---- Live trading (explicit opt-in) ----
                if (not DRY_RUN) and ENABLE_LIVE_TRADING and infra.clob is not None:
                    try:
                        # Safety cap
                        notional = float(plan["limit_price"]) * float(plan["size"])
                        if todays_notional + notional > DAILY_NOTIONAL_CAP_USD:
                            live_orders_blocked += 1
                        else:
                            from py_clob_client.clob_types import OrderArgs  # type: ignore

                            order_args = OrderArgs(
                                token_id=str(plan["token_id"]),
                                price=float(plan["limit_price"]),
                                size=float(plan["size"]),
                                side=str(plan["side"]).upper(),
                            )

                            # Use FOK to avoid leaving open orders when we expect immediate fills.
                            order = infra.clob.create_order(order_args)
                            resp = infra.clob.post_order(order, orderType="FOK", post_only=False)

                            # Try to extract order id best-effort
                            order_id = None
                            if isinstance(resp, dict):
                                order_id = resp.get("orderID") or resp.get("orderId") or resp.get("id")

                            cur.execute(
                                "UPDATE orders SET status='submitted', order_id=%s, raw_response_json=%s::jsonb WHERE client_order_id=%s",
                                (str(order_id) if order_id else None, __import__("json").dumps(resp), client_order_id),
                            )
                            live_orders_submitted += 1
                            todays_notional += notional
                    except Exception as e:
                        live_orders_blocked += 1
                        cur.execute(
                            "UPDATE orders SET status='error', error=%s WHERE client_order_id=%s",
                            (str(e), client_order_id),
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

            # Update paper position snapshot + PnL point (best-effort)
            try:
                if plans and DRY_RUN:
                    # snapshot positions for tokens we touched this run
                    token_ids = sorted({p.get("token_id") for p in plans if p.get("token_id")})
                    for token_id in token_ids:
                        cur.execute(
                            "SELECT side, price, size FROM paper_fills WHERE token_id=%s ORDER BY created_at ASC",
                            (str(token_id),),
                        )
                        rows = cur.fetchall() or []
                        pos = 0.0
                        cost = 0.0
                        for side, price, size in rows:
                            side = (side or "").lower()
                            price = float(price)
                            size = float(size)
                            if side == "buy":
                                pos += size
                                cost += price * size
                            elif side == "sell":
                                pos -= size
                                cost -= price * size
                        avg = (cost / pos) if pos > 1e-12 else None

                        snap = {
                            "token_id": str(token_id),
                            "position_size": pos,
                            "avg_entry_price": avg,
                            "fills": len(rows),
                        }
                        cur.execute(
                            """
                            INSERT INTO paper_position_snapshot(token_id, position_size, avg_entry_price, raw_json)
                            VALUES (%s,%s,%s,%s::jsonb)
                            """,
                            (
                                str(token_id),
                                float(pos),
                                float(avg) if avg is not None else None,
                                __import__("json").dumps(snap),
                            ),
                        )

                        # mark-to-mid (use live orderbook)
                        mid = None
                        if infra.clob is not None:
                            try:
                                ob = infra.clob.get_order_book(str(token_id))
                                best_bid = _as_float(ob.bids[0].price) if getattr(ob, "bids", None) else None
                                best_ask = _as_float(ob.asks[0].price) if getattr(ob, "asks", None) else None
                                if best_bid is not None and best_ask is not None:
                                    mid = (float(best_bid) + float(best_ask)) / 2.0
                            except Exception:
                                mid = None

                        unreal = None
                        if mid is not None and avg is not None:
                            unreal = (float(mid) - float(avg)) * float(pos)

                        # store pnl point
                        try:
                            market_id = str(plans[0].get("market_id") or "")
                        except Exception:
                            market_id = ""

                        raw = {
                            "token_id": str(token_id),
                            "market_id": market_id,
                            "mid": mid,
                            "position_size": pos,
                            "avg_entry_price": avg,
                            "unrealized_pnl": unreal,
                        }
                        cur.execute(
                            """
                            INSERT INTO paper_pnl_point(run_id, market_id, token_id, mid, position_size, avg_entry_price, unrealized_pnl, raw_json)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                            """,
                            (
                                run.run_id,
                                market_id,
                                str(token_id),
                                float(mid) if mid is not None else None,
                                float(pos),
                                float(avg) if avg is not None else None,
                                float(unreal) if unreal is not None else None,
                                __import__("json").dumps(raw),
                            ),
                        )
            except Exception as e:
                logger.warning("paper position/pnl snapshot failed: %s", e)

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
                """
                UPDATE bot_run
                SET discovered_count=%s,
                    trades_fetched=%s,
                    fills_inserted=%s,
                    dry_run=%s,
                    max_notional_usd=%s,
                    max_price=%s,
                    paper_plans_count=%s,
                    paper_fills_inserted=%s,
                    content_items_inserted=%s,
                    content_injection_flagged=%s,
                    signals_inserted=%s,
                    signal_snapshots_inserted=%s,
                    live_orders_submitted=%s,
                    live_orders_blocked=%s
                WHERE run_id=%s
                """,
                (
                    len(pairs),
                    len(trades),
                    inserted,
                    bool(DRY_RUN),
                    float(MAX_NOTIONAL_USD),
                    float(MAX_PRICE),
                    len(plans),
                    int(paper_fills_inserted),
                    int(content_items_inserted),
                    int(content_injection_flagged),
                    int(signals_inserted),
                    int(signal_snapshots_inserted),
                    int(live_orders_submitted),
                    int(live_orders_blocked),
                    run.run_id,
                ),
            )

        conn.commit()

        finish_run(conn, run, status="ok")

    except Exception as e:
        logger.exception("run error: %s", e)
        finish_run(conn, run, status="error", error=str(e))
        raise


if __name__ == "__main__":
    main()
