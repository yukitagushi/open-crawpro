from __future__ import annotations

import os
import psycopg


def connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required")
    return psycopg.connect(url)


def init_db(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS binance_bot_run (
              id BIGSERIAL PRIMARY KEY,
              run_id TEXT UNIQUE,
              started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              status TEXT NOT NULL DEFAULT 'running',
              error TEXT
            );

            CREATE TABLE IF NOT EXISTS binance_signal (
              id BIGSERIAL PRIMARY KEY,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              symbol TEXT NOT NULL,
              kind TEXT NOT NULL, -- ema_cross | rsi_dip
              score DOUBLE PRECISION NOT NULL,
              evidence_json JSONB
            );

            CREATE TABLE IF NOT EXISTS binance_indicator_point (
              id BIGSERIAL PRIMARY KEY,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              symbol TEXT NOT NULL,
              interval TEXT NOT NULL,
              close DOUBLE PRECISION NOT NULL,
              ema_fast DOUBLE PRECISION,
              ema_slow DOUBLE PRECISION,
              rsi DOUBLE PRECISION,
              blog_ma_score DOUBLE PRECISION,
              blog_rsi_score DOUBLE PRECISION,
              raw_json JSONB
            );

            CREATE INDEX IF NOT EXISTS idx_binance_ind_symbol_time ON binance_indicator_point(symbol, created_at);

            CREATE TABLE IF NOT EXISTS binance_balance_snapshot (
              id BIGSERIAL PRIMARY KEY,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              total_usdt_est DOUBLE PRECISION,
              raw_json JSONB
            );

            CREATE INDEX IF NOT EXISTS idx_binance_bal_time ON binance_balance_snapshot(created_at);

            CREATE TABLE IF NOT EXISTS binance_order (
              id BIGSERIAL PRIMARY KEY,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              symbol TEXT NOT NULL,
              side TEXT NOT NULL,
              order_id TEXT,
              status TEXT NOT NULL,
              quote_qty DOUBLE PRECISION,
              base_qty DOUBLE PRECISION,
              price DOUBLE PRECISION,
              take_profit_price DOUBLE PRECISION,
              stop_loss_price DOUBLE PRECISION,
              stop_limit_price DOUBLE PRECISION,
              oco_order_list_id TEXT,
              position_id BIGINT,
              raw_request_json JSONB,
              raw_response_json JSONB,
              error TEXT
            );

            CREATE TABLE IF NOT EXISTS binance_position (
              id BIGSERIAL PRIMARY KEY,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              symbol TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'open',
              entry_order_id TEXT,
              exit_order_id TEXT,
              entry_price DOUBLE PRECISION,
              entry_base_qty DOUBLE PRECISION,
              entry_quote_qty DOUBLE PRECISION,
              target_exit_price DOUBLE PRECISION,
              stop_exit_price DOUBLE PRECISION,
              planned_exit_at TIMESTAMPTZ,
              exit_price DOUBLE PRECISION,
              exit_quote_qty DOUBLE PRECISION,
              pnl_quote DOUBLE PRECISION,
              raw_json JSONB
            );

            CREATE INDEX IF NOT EXISTS idx_binance_pos_created ON binance_position(created_at);
            CREATE INDEX IF NOT EXISTS idx_binance_pos_status ON binance_position(status);
            """
        )

    # Safe schema evolution + indexes
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE binance_order ADD COLUMN IF NOT EXISTS take_profit_price DOUBLE PRECISION")
        cur.execute("ALTER TABLE binance_order ADD COLUMN IF NOT EXISTS stop_loss_price DOUBLE PRECISION")
        cur.execute("ALTER TABLE binance_order ADD COLUMN IF NOT EXISTS stop_limit_price DOUBLE PRECISION")
        cur.execute("ALTER TABLE binance_order ADD COLUMN IF NOT EXISTS oco_order_list_id TEXT")
        cur.execute("ALTER TABLE binance_order ADD COLUMN IF NOT EXISTS position_id BIGINT")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_binance_order_created ON binance_order(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_binance_order_symbol ON binance_order(symbol)")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS binance_position (
              id BIGSERIAL PRIMARY KEY,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              symbol TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'open',
              entry_order_id TEXT,
              exit_order_id TEXT,
              entry_price DOUBLE PRECISION,
              entry_base_qty DOUBLE PRECISION,
              entry_quote_qty DOUBLE PRECISION,
              target_exit_price DOUBLE PRECISION,
              stop_exit_price DOUBLE PRECISION,
              planned_exit_at TIMESTAMPTZ,
              exit_price DOUBLE PRECISION,
              exit_quote_qty DOUBLE PRECISION,
              pnl_quote DOUBLE PRECISION,
              raw_json JSONB
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_binance_pos_created ON binance_position(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_binance_pos_status ON binance_position(status)")

        # indicator table evolution
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS binance_indicator_point (
              id BIGSERIAL PRIMARY KEY,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              symbol TEXT NOT NULL,
              interval TEXT NOT NULL,
              close DOUBLE PRECISION NOT NULL,
              ema_fast DOUBLE PRECISION,
              ema_slow DOUBLE PRECISION,
              rsi DOUBLE PRECISION,
              blog_ma_score DOUBLE PRECISION,
              blog_rsi_score DOUBLE PRECISION,
              raw_json JSONB
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_binance_ind_symbol_time ON binance_indicator_point(symbol, created_at)")

        # balance snapshots
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS binance_balance_snapshot (
              id BIGSERIAL PRIMARY KEY,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              total_usdt_est DOUBLE PRECISION,
              raw_json JSONB
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_binance_bal_time ON binance_balance_snapshot(created_at)")

    conn.commit()
