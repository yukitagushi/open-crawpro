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
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS paper_plans_count INTEGER;
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS paper_fills_inserted INTEGER;
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS content_items_inserted INTEGER;
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS content_injection_flagged INTEGER;
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS signals_inserted INTEGER;
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS signal_snapshots_inserted INTEGER;

-- config snapshot (safe defaults; helps debugging)
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS dry_run BOOLEAN;
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS max_notional_usd DOUBLE PRECISION;
ALTER TABLE bot_run ADD COLUMN IF NOT EXISTS max_price DOUBLE PRECISION;

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
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

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

-- --------------------
-- Paper trade (simulated fills/positions)
-- --------------------

CREATE TABLE IF NOT EXISTS paper_fills (
  id BIGSERIAL PRIMARY KEY,
  paper_fill_id TEXT UNIQUE,
  client_order_id TEXT,
  condition_id TEXT,
  token_id TEXT,
  side TEXT NOT NULL,
  price DOUBLE PRECISION NOT NULL,
  size DOUBLE PRECISION NOT NULL,
  filled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_paper_fills_token ON paper_fills(token_id);
CREATE INDEX IF NOT EXISTS idx_paper_fills_created ON paper_fills(created_at);

CREATE TABLE IF NOT EXISTS paper_position_snapshot (
  id BIGSERIAL PRIMARY KEY,
  token_id TEXT,
  position_size DOUBLE PRECISION NOT NULL,
  avg_entry_price DOUBLE PRECISION,
  snapshot_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_paper_pos_token ON paper_position_snapshot(token_id);

-- Paper PnL time series (mark-to-mid each run)
CREATE TABLE IF NOT EXISTS paper_pnl_point (
  id BIGSERIAL PRIMARY KEY,
  run_id TEXT,
  market_id TEXT,
  token_id TEXT NOT NULL,
  mid DOUBLE PRECISION,
  position_size DOUBLE PRECISION NOT NULL,
  avg_entry_price DOUBLE PRECISION,
  unrealized_pnl DOUBLE PRECISION,
  snapshot_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_paper_pnl_token_time ON paper_pnl_point(token_id, snapshot_at);

-- --------------------
-- Content ingestion (RSS/blog/newsletters)
-- --------------------

CREATE TABLE IF NOT EXISTS content_source (
  id BIGSERIAL PRIMARY KEY,
  source_key TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL DEFAULT 'rss',
  title TEXT,
  url TEXT,
  feed_url TEXT,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS content_item (
  id BIGSERIAL PRIMARY KEY,
  source_key TEXT NOT NULL,
  item_id TEXT NOT NULL,
  url TEXT,
  title TEXT,
  author TEXT,
  summary TEXT,
  content_text TEXT,
  published_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  injection_detected BOOLEAN NOT NULL DEFAULT FALSE,
  injection_excerpt TEXT,
  tags TEXT[],
  raw_json JSONB,
  UNIQUE(source_key, item_id)
);

ALTER TABLE content_item ADD COLUMN IF NOT EXISTS tags TEXT[];

CREATE INDEX IF NOT EXISTS idx_content_item_published ON content_item(published_at);
CREATE INDEX IF NOT EXISTS idx_content_item_injection ON content_item(injection_detected);

CREATE TABLE IF NOT EXISTS content_signal (
  id BIGSERIAL PRIMARY KEY,
  source_key TEXT NOT NULL,
  item_id TEXT NOT NULL,
  score INTEGER NOT NULL,
  label TEXT NOT NULL,
  tags TEXT[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  rationale_json JSONB,
  UNIQUE(source_key, item_id)
);

ALTER TABLE content_signal ADD COLUMN IF NOT EXISTS tags TEXT[];

CREATE INDEX IF NOT EXISTS idx_content_signal_score ON content_signal(score);

CREATE TABLE IF NOT EXISTS signal_market_snapshot (
  id BIGSERIAL PRIMARY KEY,
  source_key TEXT NOT NULL,
  item_id TEXT NOT NULL,
  market_id TEXT NOT NULL,
  token_id TEXT NOT NULL,
  best_bid DOUBLE PRECISION,
  best_ask DOUBLE PRECISION,
  mid DOUBLE PRECISION,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_json JSONB,
  UNIQUE(source_key, item_id, market_id, token_id)
);

CREATE INDEX IF NOT EXISTS idx_signal_snapshot_fetched ON signal_market_snapshot(fetched_at);
