from __future__ import annotations

import os
import time
import random
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from web3 import Web3


try:
    # Official PyPI package (as requested)
    from py_clob_client.client import ClobClient  # type: ignore
except Exception as e:  # pragma: no cover
    ClobClient = None  # type: ignore
    _CLOB_IMPORT_ERR = e
else:
    _CLOB_IMPORT_ERR = None


@dataclass(frozen=True)
class InfraConfig:
    private_key: str
    polygon_rpc_url: str
    clob_api_key: str
    clob_api_secret: str
    clob_api_passphrase: str

    clob_host: str = "https://clob.polymarket.com"
    chain_id: int = 137

    retry_max: int = 5
    retry_base_seconds: float = 1.0


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def load_config_from_env() -> InfraConfig:
    """Load secrets from environment (never hard-code)."""
    load_dotenv(override=False)

    return InfraConfig(
        private_key=_require_env("PRIVATE_KEY"),
        polygon_rpc_url=_require_env("POLYGON_RPC_URL"),
        clob_api_key=_require_env("CLOB_API_KEY"),
        clob_api_secret=_require_env("CLOB_API_SECRET"),
        clob_api_passphrase=_require_env("CLOB_API_PASSPHRASE"),
        clob_host=os.getenv("CLOB_HOST", "https://clob.polymarket.com"),
        chain_id=int(os.getenv("CHAIN_ID", "137")),
        retry_max=int(os.getenv("RETRY_MAX", "5")),
        retry_base_seconds=float(os.getenv("RETRY_BASE_SECONDS", "1.0")),
    )


class Infra:
    """Holds Web3 + CLOB client with retryable connection init."""

    def __init__(self, cfg: InfraConfig):
        self.cfg = cfg
        self.w3: Optional[Web3] = None
        self.address: Optional[str] = None
        self.clob = None

    def _sleep_backoff(self, attempt: int) -> None:
        base = self.cfg.retry_base_seconds * (2 ** attempt)
        jitter = random.uniform(0, 0.25 * base)
        time.sleep(base + jitter)

    def connect_polygon(self) -> None:
        self.w3 = Web3(Web3.HTTPProvider(self.cfg.polygon_rpc_url, request_kwargs={"timeout": 20}))
        if not self.w3.is_connected():
            raise RuntimeError("Web3 could not connect to POLYGON_RPC_URL")

        acct = self.w3.eth.account.from_key(self.cfg.private_key)
        self.address = acct.address
        # sanity call
        _ = self.w3.eth.get_block_number()

    def connect_clob(self) -> None:
        if ClobClient is None:
            raise RuntimeError(
                "py-clob-client is not importable in this environment. "
                "Most likely Python is too old (requires >=3.9.10). "
                f"Import error: {_CLOB_IMPORT_ERR}"
            )

        # py-clob-client (0.34.x) expects:
        #   ClobClient(host, chain_id=..., key=<private_key>, creds=ApiCreds(...))
        from py_clob_client.clob_types import ApiCreds  # type: ignore

        self.clob = ClobClient(
            self.cfg.clob_host,
            chain_id=self.cfg.chain_id,
            key=self.cfg.private_key,
            creds=ApiCreds(
                api_key=self.cfg.clob_api_key,
                api_secret=self.cfg.clob_api_secret,
                api_passphrase=self.cfg.clob_api_passphrase,
            ),
        )

    def connect(self) -> None:
        last_err: Optional[Exception] = None
        for attempt in range(self.cfg.retry_max):
            try:
                self.connect_polygon()
                self.connect_clob()
                return
            except Exception as e:
                last_err = e
                if attempt < self.cfg.retry_max - 1:
                    self._sleep_backoff(attempt)
                    continue
        raise RuntimeError(f"Infra.connect failed after {self.cfg.retry_max} attempts: {last_err}")


if __name__ == "__main__":
    cfg = load_config_from_env()
    infra = Infra(cfg)
    infra.connect()
    print("OK")
    print("address:", infra.address)
    print("polygon block:", infra.w3.eth.get_block_number() if infra.w3 else None)
    print("clob host:", cfg.clob_host)
