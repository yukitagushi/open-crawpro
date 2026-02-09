"""SQLite persistence for Polymarket bot.

Goals:
- zero external services needed for v0
- idempotent initialization
- safe, append-only-ish logs for orders/fills/positions

NOTE: keep schema.sql as the source of truth.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


DEFAULT_DB_PATH = Path(__file__).resolve().parent / "bot.sqlite"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


@dataclass
class BotRun:
    run_id: str


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open SQLite DB and apply schema.sql."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = _connect(path)

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()
    return conn


def start_run(conn: sqlite3.Connection, run_id: Optional[str] = None) -> BotRun:
    rid = run_id or str(uuid.uuid4())
    conn.execute(
        "INSERT OR IGNORE INTO bot_run(run_id, status) VALUES (?, 'running')",
        (rid,),
    )
    conn.commit()
    return BotRun(run_id=rid)


def finish_run(conn: sqlite3.Connection, run: BotRun, status: str = "ok", error: str | None = None) -> None:
    conn.execute(
        "UPDATE bot_run SET finished_at=datetime('now'), status=?, error=? WHERE run_id=?",
        (status, error, run.run_id),
    )
    conn.commit()


def env_db_path() -> Optional[str]:
    """Optional override: POLYMARKET_BOT_DB_PATH."""
    return os.getenv("POLYMARKET_BOT_DB_PATH")
