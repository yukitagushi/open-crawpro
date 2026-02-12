"""Theme tagging for content items/signals.

Simple keyword-based tags (Phase 3, no LLM).
Content is untrusted data: tags are just metadata.
"""

from __future__ import annotations

from dataclasses import dataclass


TAG_RULES: dict[str, list[str]] = {
    # Assets / topics
    "BTC": ["btc", "bitcoin", "ビットコイン"],
    "ETH": ["eth", "ethereum", "イーサ", "イーサリアム"],
    "マクロ": ["cpi", "inflation", "rate", "fomc", "fed", "利上げ", "金利", "インフレ"],
    "ETF": ["etf"],
    "規制": ["sec", "regulation", "lawsuit", "規制", "訴訟"],
    "取引所": ["exchange", "binance", "coinbase", "取引所"],
    "DeFi": ["defi", "dex", "uniswap", "aave"],
    "ステーブル": ["usdc", "usdt", "stablecoin", "ステーブル"],

    # Technical indicators / chart methods
    "RSI": ["rsi"],
    "MACD": ["macd"],
    "ボリンジャー": ["bollinger", "ボリンジャ"],
    "移動平均": ["moving average", "ma ", "ma:", "ema", "sma", "移動平均"],
    "出来高": ["volume", "出来高"],
    "サポレジ": ["support", "resistance", "サポート", "レジスタンス", "サポレジ"],
    "トレンドライン": ["trendline", "トレンドライン"],
    "ブレイクアウト": ["breakout", "ブレイク"],
}


def extract_tags(title: str | None, summary: str | None, content_text: str | None, *, max_tags: int = 10) -> list[str]:
    text = "\n".join([title or "", summary or "", content_text or ""]).lower()
    if not text.strip():
        return []

    out: list[str] = []
    for tag, keys in TAG_RULES.items():
        for k in keys:
            if k.lower() in text:
                out.append(tag)
                break

    # stable order, limit size
    dedup = []
    seen = set()
    for t in out:
        if t in seen:
            continue
        seen.add(t)
        dedup.append(t)
    return dedup[:max_tags]
