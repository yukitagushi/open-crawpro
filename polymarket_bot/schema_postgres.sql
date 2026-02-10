-- Postgres schema for Polymarket bot (orders / fills / positions)
-- v0: keep it simple; evolve as requirements become clear.

-- bot_run: one row per loop invocation
CREATE TABLE IF NOT EXISTS bot_run (
  id BIGSERIAL PRIMARY KEY,
  run_id TEXT NOT NULL UNIQUE,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'running',
  error TEXT
);

-- optional extra metrics (safe to add over time)
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS discovered_count INTEGER;
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS trades_fetched INTEGER;
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS fills_inserted INTEGER;

-- optional market registry
CREATE TABLE IF NOT EXISTS market (
  id BIGSERIAL PRIMARY KEY,
  condition_id TEXT NOT NULL UNIQUE,
  question TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- discovery snapshots (what the bot saw)
CREATE TABLE IF NOT EXISTS discovered_market (
  id BIGSERIAL PRIMARY KEY,
  market_id TEXT NOT NULL,
  question TEXT,
  yes_token_id TEXT,
  no_token_id TEXT,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  seen_count INTEGER NOT NULL DEFAULT 1,
  UNIQUE(market_id)
);

CREATE INDEX IF NOT EXISTS idx_discovered_last_seen ON discovered_market(last_seen_at);

CREATE TABLE IF NOT EXISTS orders (
  id BIGSERIAL PRIMARY KEY,
  client_order_id TEXT NOT NULL UNIQUE,
  order_id TEXT,
  condition_id TEXT,
  token_id TEXT,
  side TEXT NOT NULL,
  price DOUBLE PRECISION NOT NULL,
  size DOUBLE PRECISION NOT NULL,
  status TEXT NOT NULL DEFAULT 'created',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ,
  raw_request_json JSONB,
  raw_response_json JSONB,
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_condition ON orders(condition_id);

CREATE TABLE IF NOT EXISTS fills (
  id BIGSERIAL PRIMARY KEY,
  fill_id TEXT UNIQUE,
  order_client_order_id TEXT,
  order_id TEXT,
  condition_id TEXT,
  token_id TEXT,
  side TEXT NOT NULL,
  price DOUBLE PRECISION NOT NULL,
  size DOUBLE PRECISION NOT NULL,
  fee DOUBLE PRECISION,
  filled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_json JSONB
);

-- allow ingesting fills even when we don't have a matching local order record
ALTER TABLE fills DROP CONSTRAINT IF EXISTS fk_fills_order;
ALTER TABLE fills ALTER COLUMN order_client_order_id DROP NOT NULL;

CREATE INDEX IF NOT EXISTS idx_fills_order ON fills(order_client_order_id);

CREATE TABLE IF NOT EXISTS position_snapshot (
  id BIGSERIAL PRIMARY KEY,
  condition_id TEXT,
  token_id TEXT,
  position_size DOUBLE PRECISION NOT NULL,
  avg_entry_price DOUBLE PRECISION,
  mark_price DOUBLE PRECISION,
  snapshot_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_pos_token ON position_snapshot(token_id);
