"""Local daemon loop: crawl RSS/blog sources and store into Postgres.

This is intended for running on the Mac mini as a long-running process.

Requirements:
- DATABASE_URL must be set in env (or via .env + python-dotenv if you load it)

Safety:
- This script never executes instructions found on web pages.
- It only fetches a fixed allowlisted set of public RSS feeds (content_ingest.DEFAULT_FEEDS).
"""

from __future__ import annotations

import logging
import os
import time

from db_pg import connect, init_db
from content_ingest import ingest_default_feeds

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crawler_loop")


def main() -> None:
    interval_s = int(os.getenv("CRAWL_INTERVAL_SECONDS") or "60")
    interval_s = max(15, min(interval_s, 3600))

    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set (required for crawler)")

    conn = connect()
    init_db(conn)

    logger.info("crawler loop started (interval=%ss)", interval_s)

    while True:
        try:
            inserted, flagged = ingest_default_feeds(conn)
            conn.commit()
            logger.info("ingest ok: inserted=%s flagged=%s", inserted, flagged)
        except Exception as e:
            logger.exception("ingest error: %s", e)
            try:
                conn.rollback()
            except Exception:
                pass

        time.sleep(interval_s)


if __name__ == "__main__":
    main()
