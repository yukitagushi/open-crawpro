-- SQLite schema for Polymarket bot (orders / fills / positions)
-- v0: keep it simple; evolve as requirements become clear.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- One row per bot invocation / loop (useful for debugging)
CREATE TABLE IF NOT EXISTS bot_run (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,              -- UUID or timestamp string
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at TEXT,
  status TEXT NOT NULL DEFAULT 'running', -- running|ok|error
  error TEXT,
  UNIQUE(run_id)
);

-- Polymarket market registry (optional but handy)
CREATE TABLE IF NOT EXISTS market (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  condition_id TEXT NOT NULL,        -- Polymarket condition id
  question TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(condition_id)
);

-- Orders we attempt / place
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_order_id TEXT NOT NULL,     -- our idempotency key
  order_id TEXT,                     -- exchange/broker order id
  condition_id TEXT,
  token_id TEXT,                     -- outcome token id (if applicable)
  side TEXT NOT NULL,                -- buy|sell
  price REAL NOT NULL,
  size REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'created', -- created|submitted|open|filled|canceled|rejected|error
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT,
  raw_request_json TEXT,
  raw_response_json TEXT,
  error TEXT,
  UNIQUE(client_order_id)
);

-- Fills / trades as reported
CREATE TABLE IF NOT EXISTS fills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fill_id TEXT,                      -- exchange fill id (if any)
  order_client_order_id TEXT NOT NULL,
  order_id TEXT,
  condition_id TEXT,
  token_id TEXT,
  side TEXT NOT NULL,
  price REAL NOT NULL,
  size REAL NOT NULL,
  fee REAL,
  filled_at TEXT,                    -- if provider gives timestamp
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  raw_json TEXT,
  UNIQUE(fill_id),
  FOREIGN KEY(order_client_order_id) REFERENCES orders(client_order_id) ON DELETE CASCADE
);

-- Snapshot of position (optional, if we poll balances/positions)
CREATE TABLE IF NOT EXISTS position_snapshot (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  condition_id TEXT,
  token_id TEXT,
  position_size REAL NOT NULL,
  avg_entry_price REAL,
  mark_price REAL,
  snapshot_at TEXT NOT NULL DEFAULT (datetime('now')),
  raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_condition ON orders(condition_id);
CREATE INDEX IF NOT EXISTS idx_fills_order ON fills(order_client_order_id);
CREATE INDEX IF NOT EXISTS idx_pos_token ON position_snapshot(token_id);
