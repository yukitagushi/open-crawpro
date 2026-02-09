"""Generate .env template (Step3 request).

We never write secrets automatically; we generate a template file.
"""

from __future__ import annotations

from pathlib import Path

TEMPLATE = """# Wallet
PRIVATE_KEY=
POLYGON_RPC_URL=

# Polymarket CLOB credentials
CLOB_API_KEY=
CLOB_API_SECRET=
CLOB_API_PASSPHRASE=

# Optional
CLOB_HOST=https://clob.polymarket.com
CHAIN_ID=137
RETRY_MAX=5
RETRY_BASE_SECONDS=1.0
"""


def write_env_template(path: str | Path = ".env.template") -> Path:
    p = Path(path)
    p.write_text(TEMPLATE, encoding="utf-8")
    return p


if __name__ == "__main__":
    out = write_env_template()
    print(f"wrote: {out}")
