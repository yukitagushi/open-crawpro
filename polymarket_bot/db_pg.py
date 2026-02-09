"""Postgres persistence for Polymarket bot.

- Designed for GitHub Actions + cloud Postgres (Neon/Supabase)
- Idempotent schema apply via schema_postgres.sql

Env:
- DATABASE_URL (preferred)

This module does NOT manage connection pooling; keep it simple for cron-style runs.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import psycopg


SCHEMA_PATH = Path(__file__).resolve().parent / "schema_postgres.sql"


@dataclass
class BotRun:
    run_id: str


def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for Postgres mode")
    return url


def connect(url: Optional[str] = None) -> psycopg.Connection:
    return psycopg.connect(url or database_url())


def init_db(conn: psycopg.Connection) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    conn.commit()


def start_run(conn: psycopg.Connection, run_id: Optional[str] = None) -> BotRun:
    rid = run_id or str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO bot_run(run_id, status) VALUES (%s, 'running') ON CONFLICT (run_id) DO NOTHING",
            (rid,),
        )
    conn.commit()
    return BotRun(run_id=rid)


def finish_run(conn: psycopg.Connection, run: BotRun, status: str = "ok", error: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE bot_run SET finished_at=now(), status=%s, error=%s WHERE run_id=%s",
            (status, error, run.run_id),
        )
    conn.commit()
