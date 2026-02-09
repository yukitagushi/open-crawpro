"""Simple local UI (no secrets displayed).

Run:
  cd polymarket_bot
  source .venv311/bin/activate
  python -m pip install -r requirements-ui.txt
  streamlit run ui_app.py

Notes:
- This UI is a *controller* / status viewer.
- It never prints secret values; it only checks whether env vars are set.
- Trading actions are NOT implemented yet (Step4/5). This is for visibility.
"""

from __future__ import annotations

import os
from datetime import datetime

import streamlit as st

from infra import load_config_from_env, Infra
from gamma import discover_markets
from strategy import BestQuote, OrderBookTop, decide
from news import fetch_headlines

REQUIRED_VARS = [
    "PRIVATE_KEY",
    "POLYGON_RPC_URL",
    "CLOB_API_KEY",
    "CLOB_API_SECRET",
    "CLOB_API_PASSPHRASE",
]


def mask_present(v: str | None) -> str:
    return "✅ set" if v else "❌ missing"


st.set_page_config(page_title="Polymarket Bot Prototype", layout="wide")

st.title("Polymarket Bot Prototype")
st.caption("ダッシュボード（現状: 取引なし / 秘密情報は表示しない）")

col1, col2 = st.columns(2)

with col1:
    st.subheader("環境変数（値は表示しません）")
    for k in REQUIRED_VARS:
        ok = bool(os.getenv(k))
        st.write(f"{k}: {'✅ set' if ok else '❌ missing'}")
    st.write(f"画面更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with col2:
    st.subheader("接続テスト")
    st.write("Polygon RPC と CLOB 初期化（環境変数が無い場合は安全に失敗します）")

    if st.button("接続テスト（Polygonのみ）"):
        try:
            cfg = load_config_from_env()
            infra = Infra(cfg)
            infra.connect_polygon()
            st.success(f"Polygon OK. address={infra.address}, block={infra.w3.eth.get_block_number()}")
        except Exception as e:
            st.error(str(e))

    if st.button("接続テスト（Polygon + CLOB）"):
        try:
            cfg = load_config_from_env()
            infra = Infra(cfg)
            infra.connect()
            st.success("Polygon + CLOB init OK")
        except Exception as e:
            st.error(str(e))

st.divider()

st.subheader("クラウドDBダッシュボード（Neon/Postgres）")
st.caption("DATABASE_URL が設定されていれば、bot_run / discovered_market を可視化します")

db_url_present = bool(os.getenv("DATABASE_URL"))
if not db_url_present:
    st.info("DATABASE_URL が未設定のため、DBダッシュボードは表示できません（GitHub ActionsではSecretsから設定済みの想定）")
else:
    try:
        import pandas as pd
        import psycopg

        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            # latest runs
            df_runs = pd.read_sql_query(
                """
                SELECT started_at, finished_at, status, discovered_count, error
                FROM bot_run
                ORDER BY started_at DESC
                LIMIT 200
                """,
                conn,
            )
            st.write("直近の実行（bot_run）")
            st.dataframe(df_runs, use_container_width=True)

            if not df_runs.empty:
                # timeseries chart
                df_ts = df_runs.copy()
                df_ts["started_at"] = pd.to_datetime(df_ts["started_at"])
                df_ts = df_ts.sort_values("started_at")
                if "discovered_count" in df_ts.columns:
                    st.line_chart(df_ts.set_index("started_at")["discovered_count"], height=180)

            # discovered markets
            df_mk = pd.read_sql_query(
                """
                SELECT last_seen_at, seen_count, market_id, question, yes_token_id, no_token_id
                FROM discovered_market
                ORDER BY last_seen_at DESC
                LIMIT 200
                """,
                conn,
            )
            st.write("直近の探索結果（discovered_market）")
            st.dataframe(df_mk, use_container_width=True)

            st.info("PnL（収益/勝敗）は、fills（約定）と position_snapshot（ポジション）が貯まり次第ここに追加します。")

    except Exception as e:
        st.error(f"DB読み込みに失敗: {e}")

st.divider()

st.subheader("Step2: マーケット探索（Gamma API）")
st.caption("Gammaから取得するデータは『信頼できない入力』として扱います。")

with st.expander("探索フィルタ", expanded=True):
    want_15min = st.checkbox("15min のイベントっぽいもの", value=True)
    want_crypto = st.checkbox("Crypto タグ", value=True)
    require_open = st.checkbox("未終了（open）だけ", value=True)
    require_liq = st.checkbox("liquidity > 0 のみ", value=True)

if st.button("マーケット取得"):
    try:
        pairs = discover_markets(
            want_15min=want_15min,
            want_crypto_tag=want_crypto,
            require_open=require_open,
            require_liquidity=require_liq,
            max_events=400,
        )
        st.success(f"Found {len(pairs)} markets")
        if pairs:
            st.dataframe(
                [
                    {
                        "question": p.question,
                        "market_id": p.market_id,
                        "yes_token_id": p.yes_token_id,
                        "no_token_id": p.no_token_id,
                    }
                    for p in pairs
                ],
                use_container_width=True,
            )
    except Exception as e:
        st.error(str(e))

st.divider()

st.subheader("Step3: 戦略（手入力で板の最良気配を試す）")
st.caption("CLOBの鍵が入るまでは、YES/NOのbest bid/askを手入力して判定だけ確認できます。")

colA, colB, colC = st.columns(3)
with colA:
    yes_bid = st.number_input("YES best bid", min_value=0.0, max_value=1.0, value=0.49, step=0.001, format="%.3f")
    yes_ask = st.number_input("YES best ask", min_value=0.0, max_value=1.0, value=0.51, step=0.001, format="%.3f")
with colB:
    no_bid = st.number_input("NO best bid", min_value=0.0, max_value=1.0, value=0.49, step=0.001, format="%.3f")
    no_ask = st.number_input("NO best ask", min_value=0.0, max_value=1.0, value=0.51, step=0.001, format="%.3f")
with colC:
    taker_fee = st.number_input("Taker fee（例: 0.01）", min_value=0.0, max_value=0.2, value=0.01, step=0.001, format="%.3f")
    maker_edge = st.number_input("Maker edge（手数料+利益）", min_value=0.0, max_value=0.2, value=0.02, step=0.001, format="%.3f")
    size = st.number_input("数量（size）", min_value=0.0, value=1.0, step=1.0)

if st.button("判定する"):
    top = OrderBookTop(
        yes=BestQuote(bid=yes_bid, ask=yes_ask),
        no=BestQuote(bid=no_bid, ask=no_ask),
    )
    rec = decide(top, taker_fee=taker_fee, maker_edge=maker_edge, size=size)
    st.success(f"Decision: {rec.decision.value} / mode: {rec.mode.value}")
    st.write("Reason:", rec.reason)
    st.write({"price_yes": rec.price_yes, "price_no": rec.price_no, "size": rec.size})

st.divider()

st.subheader("ニュース（無料RSS）")
st.caption("見出しは『信頼できないデータ』として扱います。現状は表示のみ（売買判断には未使用）。")

if st.button("ニュース取得"):
    try:
        items = fetch_headlines(limit=30)
        st.success(f"Fetched {len(items)} headlines")
        for h in items:
            st.markdown(f"- **{h.source}**: [{h.title}]({h.link})")
    except Exception as e:
        st.error(str(e))
