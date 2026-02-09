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

-- optional market registry
CREATE TABLE IF NOT EXISTS market (
  id BIGSERIAL PRIMARY KEY,
  condition_id TEXT NOT NULL UNIQUE,
  question TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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
  order_client_order_id TEXT NOT NULL,
  order_id TEXT,
  condition_id TEXT,
  token_id TEXT,
  side TEXT NOT NULL,
  price DOUBLE PRECISION NOT NULL,
  size DOUBLE PRECISION NOT NULL,
  fee DOUBLE PRECISION,
  filled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_json JSONB,
  CONSTRAINT fk_fills_order
    FOREIGN KEY(order_client_order_id)
    REFERENCES orders(client_order_id)
    ON DELETE CASCADE
);

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
