from __future__ import annotations

from dataclasses import dataclass


def ema(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    k = 2 / (period + 1)
    # seed with SMA
    sma = sum(values[:period]) / period
    e = sma
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def rsi(values: list[float], period: int = 14) -> float | None:
    if period <= 0 or len(values) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        ch = values[i] - values[i - 1]
        if ch >= 0:
            gains += ch
        else:
            losses -= ch
    avg_gain = gains / period
    avg_loss = losses / period
    for i in range(period + 1, len(values)):
        ch = values[i] - values[i - 1]
        gain = ch if ch > 0 else 0.0
        loss = -ch if ch < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
