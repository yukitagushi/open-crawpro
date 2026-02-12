from __future__ import annotations

import os

from dotenv import load_dotenv

from binance_api import BinanceApi


def main() -> None:
    load_dotenv(override=False)
    api_key = os.getenv("BINANCE_API_KEY") or ""
    api_secret = os.getenv("BINANCE_API_SECRET") or ""
    base_url = os.getenv("BINANCE_BASE_URL") or "https://api.binance.com"

    if not api_key or not api_secret:
        raise RuntimeError("BINANCE_API_KEY/SECRET required")

    api = BinanceApi(api_key, api_secret, base_url=base_url)

    print("base_url:", base_url)
    print("server_time:", api.server_time())
    print("klines BTCUSDT len:", len(api.klines("BTCUSDT", os.getenv("INTERVAL") or "15m", limit=3)))

    # Signed endpoint
    acct = api.account()
    print("account ok. keys:", list(acct.keys()))


if __name__ == "__main__":
    main()
