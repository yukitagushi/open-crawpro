from __future__ import annotations

import hashlib
import hmac
import os
import time
from urllib.parse import urlencode

import requests


class BinanceApi:
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.binance.com"):
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": api_key})

    def _sign(self, params: dict) -> str:
        qs = urlencode(params, doseq=True)
        sig = hmac.new(self.api_secret, qs.encode("utf-8"), hashlib.sha256).hexdigest()
        return qs + "&signature=" + sig

    def server_time(self) -> int:
        r = requests.get(self.base_url + "/api/v3/time", timeout=10)
        r.raise_for_status()
        return int(r.json()["serverTime"])

    def klines(self, symbol: str, interval: str, limit: int = 200) -> list:
        r = requests.get(
            self.base_url + "/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def exchange_info(self, symbol: str) -> dict:
        r = requests.get(self.base_url + "/api/v3/exchangeInfo", params={"symbol": symbol}, timeout=10)
        r.raise_for_status()
        return r.json()

    def account(self) -> dict:
        ts = self.server_time()
        params = {"timestamp": ts, "recvWindow": 5000}
        q = self._sign(params)
        r = self.session.get(self.base_url + "/api/v3/account?" + q, timeout=10)
        r.raise_for_status()
        return r.json()

    def new_order_market_buy_quote(self, symbol: str, quote_qty: float) -> dict:
        # MARKET BUY with quoteOrderQty is easiest for a "$1" constraint.
        ts = self.server_time()
        params = {
            "symbol": symbol,
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": f"{quote_qty:.2f}",
            "timestamp": ts,
            "recvWindow": 5000,
        }
        q = self._sign(params)
        r = self.session.post(self.base_url + "/api/v3/order", data=q, timeout=10)
        r.raise_for_status()
        return r.json()

    def new_oco_sell(self, symbol: str, quantity: str, price: str, stop_price: str, stop_limit_price: str) -> dict:
        ts = self.server_time()
        params = {
            "symbol": symbol,
            "side": "SELL",
            "quantity": quantity,
            "price": price,
            "stopPrice": stop_price,
            "stopLimitPrice": stop_limit_price,
            "stopLimitTimeInForce": "GTC",
            "timestamp": ts,
            "recvWindow": 5000,
        }
        q = self._sign(params)
        r = self.session.post(self.base_url + "/api/v3/order/oco", data=q, timeout=10)
        r.raise_for_status()
        return r.json()
