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


st.set_page_config(
    page_title="Polymarket Bot Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Light, universal UI styling (ChatGPT-like accent) ---
st.markdown(
    """
<style>
  /* Reduce visual noise */
  .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
  /* Headings */
  h1, h2, h3 { letter-spacing: -0.02em; }
  /* Card style */
  .oc-card {
    background: #FFFFFF;
    border: 1px solid rgba(17,24,39,0.08);
    border-radius: 14px;
    padding: 14px 16px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  }
  .oc-muted { color: rgba(17,24,39,0.65); font-size: 0.92rem; }
  .oc-kpi { font-size: 1.25rem; font-weight: 700; }
  .oc-row { display: flex; gap: 12px; flex-wrap: wrap; }
  .oc-pill {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 10px; border-radius: 999px;
    border: 1px solid rgba(17,24,39,0.10);
    background: #F7F7F8;
    font-size: 0.9rem;
  }
  .oc-dot { width: 8px; height: 8px; border-radius: 999px; display:inline-block; }
  .oc-dot.ok { background: #10A37F; }
  .oc-dot.bad { background: #EF4444; }
  /* Streamlit tweaks */
  div[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid rgba(17,24,39,0.08); border-radius: 14px; padding: 10px 12px; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Polymarket Bot Dashboard")
st.caption("白ベースのシンプルUI（取引はまだ実装前 / 秘密情報は表示しません）")

# Sidebar navigation
page = st.sidebar.radio(
    "メニュー",
    ["Overview", "DB Dashboard", "Market Discovery", "Strategy Sandbox", "News", "Logs"],
    index=0,
)

# --- Overview ---
if page == "Overview":
    st.subheader("Overview")
    st.markdown("<div class='oc-muted'>稼働状況と接続状態を、見やすくまとめます。</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("DB (DATABASE_URL)", "READY" if os.getenv("DATABASE_URL") else "MISSING")
    with c2:
        st.metric("Secrets (local)", "OK" if all(os.getenv(k) for k in REQUIRED_VARS) else "CHECK")
    with c3:
        st.metric("Last refresh", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    st.markdown("### 接続チェック（ローカル用）")
    st.markdown("<div class='oc-muted'>GitHub Actionsでは不要。ローカルで確認したい時だけ使ってください。</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='oc-card'>", unsafe_allow_html=True)
        st.write("環境変数（値は表示しません）")
        for k in REQUIRED_VARS:
            ok = bool(os.getenv(k))
            st.markdown(
                f"<span class='oc-pill'><span class='oc-dot {'ok' if ok else 'bad'}'></span><b>{k}</b> — {'set' if ok else 'missing'}</span>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='oc-card'>", unsafe_allow_html=True)
        st.write("接続テスト")
        st.markdown("<div class='oc-muted'>Polygon RPC と CLOB 初期化（環境変数が無い場合は安全に失敗します）</div>", unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        with b1:
            if st.button("Polygonのみ", use_container_width=True):
                try:
                    cfg = load_config_from_env()
                    infra = Infra(cfg)
                    infra.connect_polygon()
                    st.success(f"Polygon OK. address={infra.address}, block={infra.w3.eth.get_block_number()}")
                except Exception as e:
                    st.error(str(e))
        with b2:
            if st.button("Polygon + CLOB", use_container_width=True):
                try:
                    cfg = load_config_from_env()
                    infra = Infra(cfg)
                    infra.connect()
                    st.success("Polygon + CLOB init OK")
                except Exception as e:
                    st.error(str(e))

        st.markdown("</div>", unsafe_allow_html=True)

# --- DB Dashboard ---
elif page == "DB Dashboard":
    st.subheader("DB Dashboard（Neon/Postgres）")
    st.markdown("<div class='oc-muted'>DBに溜まったデータを、表とグラフで確認します。</div>", unsafe_allow_html=True)

    db_url_present = bool(os.getenv("DATABASE_URL"))
    if not db_url_present:
        st.info("DATABASE_URL が未設定です。ローカルUIからDBを見る場合は、環境変数 DATABASE_URL をセットしてください。")
    else:
        try:
            import pandas as pd
            import psycopg

            with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
                df_runs = pd.read_sql_query(
                    """
                    SELECT started_at, finished_at, status, discovered_count, error
                    FROM bot_run
                    ORDER BY started_at DESC
                    LIMIT 200
                    """,
                    conn,
                )

                top1, top2, top3 = st.columns(3)
                with top1:
                    st.metric("Runs (last 200)", int(len(df_runs)))
                with top2:
                    ok = int((df_runs["status"] == "ok").sum()) if not df_runs.empty else 0
                    st.metric("OK", ok)
                with top3:
                    last = df_runs.iloc[0]["started_at"] if not df_runs.empty else None
                    st.metric("Latest", str(last) if last is not None else "-")

                st.markdown("### 実行履歴（bot_run）")
                st.dataframe(df_runs, use_container_width=True)

                if not df_runs.empty and "discovered_count" in df_runs.columns:
                    df_ts = df_runs.copy()
                    df_ts["started_at"] = pd.to_datetime(df_ts["started_at"])
                    df_ts = df_ts.sort_values("started_at")
                    st.markdown("### 探索件数（時系列）")
                    st.line_chart(df_ts.set_index("started_at")["discovered_count"], height=200)

                df_mk = pd.read_sql_query(
                    """
                    SELECT last_seen_at, seen_count, market_id, question, yes_token_id, no_token_id
                    FROM discovered_market
                    ORDER BY last_seen_at DESC
                    LIMIT 200
                    """,
                    conn,
                )
                st.markdown("### 直近の探索結果（discovered_market）")
                st.dataframe(df_mk, use_container_width=True)

                st.info("PnL（収益/勝敗）は、fills（約定）と position_snapshot（ポジション）を保存し始めたらここに追加します。")

        except Exception as e:
            st.error(f"DB読み込みに失敗: {e}")

# --- Market Discovery ---
elif page == "Market Discovery":
    st.subheader("Market Discovery（Gamma API）")
    st.markdown("<div class='oc-muted'>Gammaから取得するデータは『信頼できない入力』として扱います（表示・保存のみ）。</div>", unsafe_allow_html=True)

    with st.expander("探索フィルタ", expanded=True):
        want_15min = st.checkbox("15min のイベントっぽいもの", value=True)
        want_crypto = st.checkbox("Crypto タグ", value=True)
        require_open = st.checkbox("未終了（open）だけ", value=True)
        require_liq = st.checkbox("liquidity > 0 のみ", value=True)

    if st.button("マーケット取得", use_container_width=True):
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

# --- Strategy Sandbox ---
elif page == "Strategy Sandbox":
    st.subheader("Strategy Sandbox")
    st.markdown("<div class='oc-muted'>板情報を手入力して、判定ロジックだけ試せます。</div>", unsafe_allow_html=True)

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

    if st.button("判定する", use_container_width=True):
        top = OrderBookTop(
            yes=BestQuote(bid=yes_bid, ask=yes_ask),
            no=BestQuote(bid=no_bid, ask=no_ask),
        )
        rec = decide(top, taker_fee=taker_fee, maker_edge=maker_edge, size=size)

        # Show the exact arb inequality for clarity
        lhs = yes_ask + no_ask
        rhs = 1.0 - 2.0 * taker_fee
        st.markdown("#### 判定の根拠")
        st.markdown(
            f"- Negative Risk Arb 条件: `YES_ask + NO_ask < 1 - 2*taker_fee`  \n"
            f"- 今回: `{lhs:.4f} < {rhs:.4f}`"
        )

        if rec.mode.value == "taker_arb":
            st.success(f"判定: {rec.decision.value}（Arb / Taker）")
        elif rec.mode.value == "maker":
            st.info(f"判定: {rec.decision.value}（Maker 指値）")
        else:
            st.warning(f"判定: {rec.decision.value}")

        st.write("理由:", rec.reason)
        st.write({"price_yes": rec.price_yes, "price_no": rec.price_no, "size": rec.size})

# --- News ---
elif page == "News":
    st.subheader("News（無料RSS）")
    st.markdown("<div class='oc-muted'>見出しは『信頼できないデータ』として扱います。現状は表示のみ。</div>", unsafe_allow_html=True)

    if st.button("ニュース取得", use_container_width=True):
        try:
            items = fetch_headlines(limit=30)
            st.success(f"Fetched {len(items)} headlines")
            for h in items:
                st.markdown(f"- **{h.source}**: [{h.title}]({h.link})")
        except Exception as e:
            st.error(str(e))

# --- Logs ---
elif page == "Logs":
    st.subheader("Logs")
    st.markdown("<div class='oc-muted'>UI起動ログ（logs/ui.log）をここで確認できます。</div>", unsafe_allow_html=True)

    log_path = os.path.join(os.path.dirname(__file__), "logs", "ui.log")
    st.code(log_path)

    n = st.slider("表示行数", min_value=20, max_value=400, value=120, step=20)

    try:
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()[-n:]
            st.text("\n".join(lines))
        else:
            st.info("まだ logs/ui.log がありません。run_ui.sh で起動すると作成されます。")
    except Exception as e:
        st.error(f"ログ読み込みに失敗: {e}")

    st.markdown("### よくあるメモ")
    st.markdown(
        "- UI起動: `./scripts/run_ui.sh`（ローカル127.0.0.1固定）\n"
        "- UI停止: `./scripts/stop_ui.sh`\n"
        "- もし別PC/スマホから見たい場合は、Tailscale等の安全な経路推奨（ポート開放は非推奨）"
    )
