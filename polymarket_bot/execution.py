"""Step4: Execution skill (SAFE SKELETON).

IMPORTANT:
- This file defines the *interface* and safe error handling patterns.
- It does NOT place real orders until explicitly enabled.
- When enabled later, it must:
  - use FOK for arb legs
  - use POST_ONLY + GTC for maker
  - log failures (rate limit, balance, signature)

We also add a "dry_run" default to prevent accidental trading.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TimeInForce(str, Enum):
    FOK = "FOK"  # Fill or Kill
    GTC = "GTC"  # Good Till Cancel


@dataclass(frozen=True)
class OrderRequest:
    token_id: str
    side: str  # "buy" or "sell"
    price: float
    size: float
    tif: TimeInForce
    post_only: bool = False


@dataclass(frozen=True)
class OrderResult:
    ok: bool
    order_id: Optional[str] = None
    error: Optional[str] = None


class Execution:
    def __init__(self, infra, *, dry_run: bool = True):
        self.infra = infra
        self.dry_run = dry_run

    def place_order(self, req: OrderRequest) -> OrderResult:
        """Place one order.

        In dry_run mode, returns ok=True without sending.
        """
        if self.dry_run:
            logger.info("DRY_RUN place_order: %s", req)
            return OrderResult(ok=True, order_id="dry_run")

        # TODO: Wire to py-clob-client order placement.
        # Must catch and classify errors.
        raise NotImplementedError("Real order placement not wired yet")

    def place_arb_fok(self, yes_req: OrderRequest, no_req: OrderRequest) -> tuple[OrderResult, OrderResult]:
        """Arb execution: both legs should be FOK.

        NOTE: True atomicity may require additional coordination. This function
        defines the intended safety contract.
        """
        if yes_req.tif != TimeInForce.FOK or no_req.tif != TimeInForce.FOK:
            raise ValueError("Arb legs must use FOK")

        r1 = self.place_order(yes_req)
        r2 = self.place_order(no_req)
        return r1, r2
