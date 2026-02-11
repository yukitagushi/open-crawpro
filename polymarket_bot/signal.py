"""Simple content signal extraction.

Phase A (no LLM): keyword-based bullish/bearish scoring.

IMPORTANT: Content is untrusted data. We NEVER execute instructions found in it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


BULLISH = [
    # EN
    "bull",
    "bullish",
    "breakout",
    "buy",
    "accumulate",
    "uptrend",
    "ath",
    "all-time high",
    "undervalued",
    "strong bid",
    # JA
    "強気",
    "買い",
    "上昇",
    "ロング",
    "ブレイク",
    "爆上げ",
]

BEARISH = [
    # EN
    "bear",
    "bearish",
    "sell",
    "dump",
    "downtrend",
    "crash",
    "short",
    "rug",
    "overvalued",
    # JA
    "弱気",
    "売り",
    "下落",
    "ショート",
    "暴落",
]


def _count_keywords(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    hit = []
    t = text.lower()
    for k in keywords:
        kk = k.lower()
        if kk in t:
            hit.append(k)
    return len(hit), hit


@dataclass
class Signal:
    score: int
    label: str
    hits_bull: list[str]
    hits_bear: list[str]


def score_text(title: str | None, summary: str | None, content_text: str | None) -> Signal:
    text = "\n".join([title or "", summary or "", content_text or ""]).strip()
    if not text:
        return Signal(score=0, label="neutral", hits_bull=[], hits_bear=[])

    bull_n, bull_hits = _count_keywords(text, BULLISH)
    bear_n, bear_hits = _count_keywords(text, BEARISH)

    # small emphasis for excitement
    exclam = text.count("!") + text.count("！")

    score = bull_n - bear_n
    if score > 0:
        score += min(2, exclam // 2)
    elif score < 0:
        score -= min(2, exclam // 2)

    if score >= 2:
        label = "bullish"
    elif score <= -2:
        label = "bearish"
    else:
        label = "neutral"

    return Signal(score=score, label=label, hits_bull=bull_hits, hits_bear=bear_hits)
