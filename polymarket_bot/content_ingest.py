"""Content ingestion (RSS/blog).

- Fetches a small allowlisted set of RSS feeds
- Stores items into Postgres
- Flags prompt-injection-like text, but NEVER executes it (data only)

Design goal: low-dependency (no feedparser).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable

import requests


DEFAULT_FEEDS = [
    # General crypto news (RSS)
    ("coindesk", "CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("cointelegraph", "Cointelegraph", "https://cointelegraph.com/rss"),
    ("decrypt", "Decrypt", "https://decrypt.co/feed"),
    ("thedefiant", "The Defiant", "https://thedefiant.io/feed"),
    ("bankless", "Bankless", "https://www.bankless.com/feed"),
]


INJECTION_PATTERNS = [
    r"ignore (all|any|the) (previous|above) (instructions|directions)",
    r"system prompt",
    r"developer message",
    r"you are chatgpt",
    r"BEGIN_?PROMPT",
    r"END_?PROMPT",
    r"do not (tell|share) (anyone|the user)",
    r"reveal (your|the) (prompt|instructions)",
]

_inj_re = re.compile("|".join(f"({p})" for p in INJECTION_PATTERNS), re.IGNORECASE)


@dataclass
class FeedItem:
    source_key: str
    item_id: str
    url: str | None
    title: str | None
    author: str | None
    summary: str | None
    content_text: str | None
    published_at: str | None
    injection_detected: bool
    injection_excerpt: str | None
    raw: dict


def _text(el: ET.Element | None) -> str | None:
    if el is None:
        return None
    if el.text is None:
        return None
    t = el.text.strip()
    return t or None


def _first_text(parent: ET.Element, tags: Iterable[str]) -> str | None:
    for t in tags:
        el = parent.find(t)
        if el is not None:
            v = _text(el)
            if v:
                return v
    return None


def _hash_id(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _detect_injection(text: str | None) -> tuple[bool, str | None]:
    if not text:
        return (False, None)
    m = _inj_re.search(text)
    if not m:
        return (False, None)
    start = max(0, m.start() - 80)
    end = min(len(text), m.end() + 80)
    excerpt = text[start:end]
    # keep excerpt small
    excerpt = excerpt.replace("\n", " ")
    if len(excerpt) > 220:
        excerpt = excerpt[:220] + "…"
    return (True, excerpt)


def fetch_rss(feed_url: str, timeout: int = 15) -> str:
    resp = requests.get(
        feed_url,
        timeout=timeout,
        headers={"User-Agent": "open-crawpro/1.0 (+rss ingest)"},
    )
    resp.raise_for_status()
    return resp.text


def parse_rss(source_key: str, xml_text: str) -> list[FeedItem]:
    # Support RSS 2.0 channel/item and Atom feed/entry best-effort
    root = ET.fromstring(xml_text)

    items: list[FeedItem] = []

    # RSS 2.0
    channel = root.find("channel")
    if channel is not None:
        for it in channel.findall("item"):
            link = _first_text(it, ["link"])
            guid = _first_text(it, ["guid"]) or link or _hash_id(ET.tostring(it, encoding="utf-8").decode("utf-8"))
            title = _first_text(it, ["title"])
            author = _first_text(it, ["author", "{http://purl.org/dc/elements/1.1/}creator"])
            summary = _first_text(it, ["description"])
            content = _first_text(it, ["{http://purl.org/rss/1.0/modules/content/}encoded"]) or summary
            pub = _first_text(it, ["pubDate", "{http://purl.org/dc/elements/1.1/}date"])

            inj, excerpt = _detect_injection("\n".join([title or "", summary or "", content or ""]))

            items.append(
                FeedItem(
                    source_key=source_key,
                    item_id=str(guid),
                    url=link,
                    title=title,
                    author=author,
                    summary=summary,
                    content_text=content,
                    published_at=pub,
                    injection_detected=inj,
                    injection_excerpt=excerpt,
                    raw={"kind": "rss", "guid": guid, "link": link, "pub": pub},
                )
            )
        return items

    # Atom
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", ns):
        title = _text(entry.find("atom:title", ns))
        link_el = entry.find("atom:link", ns)
        link = link_el.attrib.get("href") if link_el is not None else None
        entry_id = _text(entry.find("atom:id", ns)) or link or _hash_id(ET.tostring(entry, encoding="utf-8").decode("utf-8"))
        author = None
        author_el = entry.find("atom:author", ns)
        if author_el is not None:
            author = _text(author_el.find("atom:name", ns))
        summary = _text(entry.find("atom:summary", ns))
        content = _text(entry.find("atom:content", ns)) or summary
        pub = _text(entry.find("atom:published", ns)) or _text(entry.find("atom:updated", ns))

        inj, excerpt = _detect_injection("\n".join([title or "", summary or "", content or ""]))

        items.append(
            FeedItem(
                source_key=source_key,
                item_id=str(entry_id),
                url=link,
                title=title,
                author=author,
                summary=summary,
                content_text=content,
                published_at=pub,
                injection_detected=inj,
                injection_excerpt=excerpt,
                raw={"kind": "atom", "id": entry_id, "link": link, "pub": pub},
            )
        )

    return items


def ingest_default_feeds(conn) -> tuple[int, int]:
    """Returns (items_inserted, injection_flagged_inserted)."""

    items_inserted = 0
    injection_flagged = 0

    with conn.cursor() as cur:
        for source_key, title, feed_url in DEFAULT_FEEDS:
            # register source
            cur.execute(
                """
                INSERT INTO content_source(source_key, kind, title, feed_url, enabled)
                VALUES (%s,'rss',%s,%s,true)
                ON CONFLICT (source_key) DO UPDATE SET
                  title=EXCLUDED.title,
                  feed_url=EXCLUDED.feed_url,
                  updated_at=now()
                """,
                (source_key, title, feed_url),
            )

            try:
                xml_text = fetch_rss(feed_url)
                parsed = parse_rss(source_key, xml_text)
            except Exception as e:
                # best-effort: keep going
                cur.execute(
                    "UPDATE content_source SET updated_at=now() WHERE source_key=%s",
                    (source_key,),
                )
                continue

            for it in parsed[:50]:
                # item_id fallback if huge
                item_id = it.item_id
                if len(item_id) > 512:
                    item_id = _hash_id(item_id)

                cur.execute(
                    """
                    INSERT INTO content_item(
                      source_key, item_id, url, title, author, summary, content_text,
                      published_at, injection_detected, injection_excerpt, raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s, NULLIF(%s,'')::timestamptz, %s,%s,%s::jsonb)
                    ON CONFLICT (source_key, item_id)
                    DO NOTHING
                    """,
                    (
                        it.source_key,
                        item_id,
                        it.url,
                        it.title,
                        it.author,
                        it.summary,
                        it.content_text,
                        it.published_at or "",
                        bool(it.injection_detected),
                        it.injection_excerpt,
                        json.dumps(it.raw),
                    ),
                )
                if cur.rowcount:
                    items_inserted += 1
                    if it.injection_detected:
                        injection_flagged += 1

            # polite pacing
            time.sleep(0.2)

    return items_inserted, injection_flagged
