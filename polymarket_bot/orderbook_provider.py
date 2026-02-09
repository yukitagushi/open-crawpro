"""Orderbook interface (connector layer).

Goal:
- Define a stable shape for obtaining top-of-book quotes.
- UI/strategy can depend on this interface.
- Implementation can be swapped (dummy vs. real CLOB) without changing strategy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass(frozen=True)
class OrderBookTop:
    bid: Optional[float]
    ask: Optional[float]


class OrderBookProvider(Protocol):
    def get_top(self, token_id: str) -> OrderBookTop:
        """Return best bid/ask for a token id."""
        ...


class DummyOrderBookProvider:
    """For UI testing without network / credentials."""

    def __init__(self, bid: float = 0.49, ask: float = 0.51):
        self.bid = bid
        self.ask = ask

    def get_top(self, token_id: str) -> OrderBookTop:
        return OrderBookTop(bid=self.bid, ask=self.ask)


class ClobOrderBookProvider:
    """Placeholder for real CLOB-backed provider.

    NOTE: This requires valid CLOB credentials and a working py-clob-client init.
    We will wire this after env vars are set.
    """

    def __init__(self, infra):
        self.infra = infra

    def get_top(self, token_id: str) -> OrderBookTop:
        # TODO: implement using py-clob-client orderbook endpoints.
        raise NotImplementedError("CLOB provider wiring pending (needs credentials)")
