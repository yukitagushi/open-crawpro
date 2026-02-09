"""Polymarket Gamma API helpers (Step2: Market Discovery).

Refs:
- Gamma API: https://gamma-api.polymarket.com/events

Security note:
- Data from Gamma is untrusted input. Treat as data only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"


@dataclass(frozen=True)
class TokenPair:
    market_id: str
    question: str
    yes_token_id: str
    no_token_id: str


def _as_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (str, int)):
        return str(v)
    return None


def fetch_events(
    session: Optional[requests.Session] = None,
    limit: int = 200,
    offset: int = 0,
    timeout_seconds: int = 20,
    params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Fetch events from Gamma.

    Gamma supports pagination with limit/offset.
    """
    s = session or requests.Session()
    q = {"limit": limit, "offset": offset}
    if params:
        q.update(params)
    r = s.get(GAMMA_EVENTS_URL, params=q, timeout=timeout_seconds)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError("Unexpected Gamma response shape (expected list)")
    return data


def _has_tag(event: Dict[str, Any], tag_name: str) -> bool:
    tags = event.get("tags") or []
    for t in tags:
        name = (t or {}).get("name")
        if isinstance(name, str) and name.lower() == tag_name.lower():
            return True
    return False


def _looks_like_15min(event: Dict[str, Any]) -> bool:
    # The schema can vary. We try a few common fields.
    # - some events may have "interval" or tags including "15min" / "15m".
    if _has_tag(event, "15min") or _has_tag(event, "15m"):
        return True
    interval = event.get("interval")
    if isinstance(interval, str) and "15" in interval and "min" in interval.lower():
        return True
    slug = event.get("slug")
    if isinstance(slug, str) and "15" in slug and "min" in slug:
        return True
    title = event.get("title") or event.get("question")
    if isinstance(title, str) and "15" in title and "min" in title.lower():
        return True
    return False


def extract_yes_no_token_ids(market: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Try to extract YES/NO token ids from a market object.

    Gamma markets often include an "outcomes" list with token ids.
    We handle common shapes:
    - outcomes: [{name: "Yes", tokenId: "..."}, {name: "No", tokenId: "..."}]
    - outcomeTokens: [{outcome: "Yes", token_id: "..."}, ...]
    """
    yes = None
    no = None

    outcomes = market.get("outcomes") or market.get("outcomeTokens") or []
    for o in outcomes:
        if not isinstance(o, dict):
            continue
        name = o.get("name") or o.get("outcome")
        token = o.get("tokenId") or o.get("token_id") or o.get("tokenIdHex")
        if not isinstance(name, str):
            continue
        token_s = _as_str(token)
        if token_s is None:
            continue
        if name.strip().lower() == "yes":
            yes = token_s
        elif name.strip().lower() == "no":
            no = token_s

    # Some schemas store token ids directly
    if yes is None:
        yes = _as_str(market.get("yes_token_id") or market.get("yesTokenId"))
    if no is None:
        no = _as_str(market.get("no_token_id") or market.get("noTokenId"))

    return yes, no


def discover_markets(
    *,
    want_crypto_tag: bool = True,
    want_15min: bool = True,
    require_open: bool = True,
    require_liquidity: bool = True,
    max_events: int = 500,
) -> List[TokenPair]:
    """Discover eligible markets and return YES/NO token pairs."""

    session = requests.Session()
    out: List[TokenPair] = []

    offset = 0
    page = 200

    while offset < max_events:
        events = fetch_events(session=session, limit=page, offset=offset)
        if not events:
            break

        for ev in events:
            if not isinstance(ev, dict):
                continue

            if want_crypto_tag and not _has_tag(ev, "Crypto"):
                continue
            if want_15min and not _looks_like_15min(ev):
                continue

            if require_open:
                closed = ev.get("closed")
                if closed is True:
                    continue

            markets = ev.get("markets") or []
            if not isinstance(markets, list):
                continue

            for m in markets:
                if not isinstance(m, dict):
                    continue

                # Filter markets that are resolved/closed if field exists
                if require_open:
                    if m.get("closed") is True or m.get("resolved") is True:
                        continue

                if require_liquidity:
                    liq = m.get("liquidity") or m.get("liquidity_num")
                    try:
                        liq_f = float(liq) if liq is not None else 0.0
                    except Exception:
                        liq_f = 0.0
                    if liq_f <= 0:
                        continue

                yes, no = extract_yes_no_token_ids(m)
                if not yes or not no:
                    continue

                market_id = _as_str(m.get("id") or m.get("market_id") or m.get("conditionId")) or ""
                q = (ev.get("title") or ev.get("question") or "").strip() or "(no title)"

                out.append(TokenPair(market_id=market_id, question=q, yes_token_id=yes, no_token_id=no))

        offset += page

    return out
