"""Risk controls / kill switch (Step5 support).

This module is purely local state + policy.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KillSwitch:
    max_consecutive_errors: int = 10
    consecutive_errors: int = 0
    tripped: bool = False

    def record_success(self) -> None:
        self.consecutive_errors = 0

    def record_error(self) -> None:
        self.consecutive_errors += 1
        if self.consecutive_errors >= self.max_consecutive_errors:
            self.tripped = True

    def assert_ok(self) -> None:
        if self.tripped:
            raise RuntimeError("KillSwitch tripped: too many consecutive errors")
