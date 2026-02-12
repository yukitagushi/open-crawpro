from __future__ import annotations

from dataclasses import dataclass

from indicators import ema, rsi


@dataclass(frozen=True)
class Signal:
    kind: str  # ema_cross | rsi_dip
    score: float
    target_pct: float
    stop_pct: float
    evidence: dict


def decide_signal(closes: list[float], *, ema_fast: int, ema_slow: int, rsi_period: int, blog_ma_score: float, blog_rsi_score: float, tp_pct: float, sl_pct: float) -> Signal | None:
    ef = ema(closes, ema_fast)
    es = ema(closes, ema_slow)
    rv = rsi(closes, rsi_period)
    if ef is None or es is None or rv is None:
        return None

    # Normalize blog preference into [0,1]
    total = max(1e-9, blog_ma_score + blog_rsi_score)
    w_ma = blog_ma_score / total
    w_rsi = blog_rsi_score / total

    # simple conditions
    ema_cross = (ef > es)
    rsi_dip = (rv < 30)

    score = 0.0
    kind = None
    if ema_cross:
        score += 0.6 * w_ma
        kind = "ema_cross"
    if rsi_dip:
        score += 0.6 * w_rsi
        kind = "rsi_dip" if kind is None else kind

    # extra: boost if both agree
    if ema_cross and rsi_dip:
        score += 0.4
        kind = "ema_cross+rsi_dip"

    if score < 0.7:
        return None

    return Signal(
        kind=kind,
        score=score,
        target_pct=tp_pct,
        stop_pct=sl_pct,
        evidence={
            "ema_fast": ef,
            "ema_slow": es,
            "rsi": rv,
            "w_ma": w_ma,
            "w_rsi": w_rsi,
        },
    )
