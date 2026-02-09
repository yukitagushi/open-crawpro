"""Step3: Strategy / Decision layer.

This module is pure logic:
- Input: orderbook best bids/asks for YES and NO tokens.
- Output: action (BUY/SELL/WAIT) with recommended order type + price/size.

Notes:
- External market/orderbook data is untrusted input.
- This module MUST NOT execute trades.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DecisionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    WAIT = "wait"


class Mode(str, Enum):
    TAKER_ARB = "taker_arb"
    MAKER = "maker"
    NONE = "none"


@dataclass(frozen=True)
class BestQuote:
    bid: Optional[float]  # best bid price
    ask: Optional[float]  # best ask price


@dataclass(frozen=True)
class OrderBookTop:
    yes: BestQuote
    no: BestQuote


@dataclass(frozen=True)
class Recommendation:
    decision: DecisionType
    mode: Mode
    reason: str

    # optional fields for execution layer
    price_yes: Optional[float] = None
    price_no: Optional[float] = None
    size: Optional[float] = None


def is_negative_risk_arb(yes_ask: float, no_ask: float, taker_fee: float) -> bool:
    """Negative risk arb condition (taker):

    Ask(YES) + Ask(NO) < 1.0 - 2 * taker_fee
    """
    return (yes_ask + no_ask) < (1.0 - (taker_fee * 2.0))


def fair_price_simple() -> tuple[float, float]:
    """Baseline fair price placeholder."""
    return 0.5, 0.5


def maker_quotes(
    fair_yes: float,
    fair_no: float,
    *,
    edge: float,
) -> tuple[float, float]:
    """Return maker quote prices around fair value.

    edge: total spread component (fee + profit margin), e.g. 0.02.

    For simplicity we quote slightly *worse* than fair (buy below fair).
    """
    yes = max(0.001, min(0.999, fair_yes - edge / 2.0))
    no = max(0.001, min(0.999, fair_no - edge / 2.0))
    return yes, no


def decide(
    top: OrderBookTop,
    *,
    taker_fee: float,
    maker_edge: float,
    size: float = 1.0,
) -> Recommendation:
    """Hybrid decision logic.

    - If negative-risk arb exists: recommend taker arb (execution uses FOK/atomic policy).
    - Else: recommend maker quotes around fair price.

    decision is BUY (meaning: place orders). SELL is reserved for future inventory mgmt.
    """

    if top.yes.ask is not None and top.no.ask is not None:
        if is_negative_risk_arb(top.yes.ask, top.no.ask, taker_fee=taker_fee):
            return Recommendation(
                decision=DecisionType.BUY,
                mode=Mode.TAKER_ARB,
                reason=f"Negative risk arb: yes_ask+no_ask={top.yes.ask+top.no.ask:.4f} < 1-2fee={1-2*taker_fee:.4f}",
                price_yes=top.yes.ask,
                price_no=top.no.ask,
                size=size,
            )

    fair_yes, fair_no = fair_price_simple()
    py, pn = maker_quotes(fair_yes, fair_no, edge=maker_edge)
    return Recommendation(
        decision=DecisionType.BUY,
        mode=Mode.MAKER,
        reason="No arb; quote maker orders around fair price (placeholder fair=0.5/0.5)",
        price_yes=py,
        price_no=pn,
        size=size,
    )
