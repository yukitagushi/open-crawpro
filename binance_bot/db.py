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
              raw_request_json JSONB,
              raw_response_json JSONB,
              error TEXT
            );
            """
        )
    conn.commit()
