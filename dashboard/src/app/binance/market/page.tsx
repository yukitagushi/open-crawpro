export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../../_components/AutoReload';

type IndRow = {
  created_at: any;
  symbol: string;
  interval: string;
  close: number;
  ema_fast: number | null;
  ema_slow: number | null;
  rsi: number | null;
  blog_ma_score: number | null;
  blog_rsi_score: number | null;
};

type BalRow = {
  created_at: any;
  total_usdt_est: number | null;
};

function fmt(ts: any) {
  if (!ts) return '-';
  const s = ts instanceof Date ? ts.toISOString() : String(ts);
  return s.replace('T', ' ').replace('Z', '');
}

export default async function Page() {
  if (!hasDatabase()) {
    return (
      <main className="container">
        <div className="card">
          <div className="h1">セットアップが必要</div>
          <div className="muted">DATABASE_URL が未設定のため、DBに接続できません。</div>
          <div style={{ marginTop: 12 }}>
            <Link href="/">← 戻る</Link>
          </div>
        </div>
      </main>
    );
  }

  const inds = await sql<IndRow>(
    `
    SELECT created_at, symbol, interval, close, ema_fast, ema_slow, rsi, blog_ma_score, blog_rsi_score
    FROM binance_indicator_point
    ORDER BY created_at DESC
    LIMIT 200
    `
  );

  const bals = await sql<BalRow>(
    `
    SELECT created_at, total_usdt_est
    FROM binance_balance_snapshot
    ORDER BY created_at DESC
    LIMIT 50
    `
  );

  return (
    <main className="container">
      <AutoReload seconds={30} />
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">Binance 市場/指標</div>
        <div className="muted">BTC/ETH 15分足の指標スナップショットと資産推定</div>
        <div style={{ marginTop: 8 }}>
          <Link href="/binance/signals">シグナル</Link>
          <span className="muted"> ・ </span>
          <Link href="/binance/orders">注文</Link>
        </div>
      </div>

      <div className="grid">
        <div className="card" style={{ gridColumn: 'span 6' }}>
          <div style={{ fontWeight: 800 }}>資産推定（USDT換算）</div>
          <div className="muted">binance_balance_snapshot.total_usdt_est</div>
          <div style={{ marginTop: 10 }}>
            {bals.length === 0 ? (
              <div className="muted">まだデータがありません</div>
            ) : (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {bals.map((r, i) => (
                  <li key={i} className="mono">
                    {fmt(r.created_at)} — {r.total_usdt_est ?? '-'}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="card" style={{ gridColumn: 'span 6' }}>
          <div style={{ fontWeight: 800 }}>直近の指標スナップショット</div>
          <div className="muted">close / EMA / RSI / ブログスコア</div>
          <div style={{ marginTop: 10, overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>時刻</th>
                  <th>銘柄</th>
                  <th>終値</th>
                  <th>EMA(9)</th>
                  <th>EMA(21)</th>
                  <th>RSI</th>
                  <th>MAスコア</th>
                  <th>RSIスコア</th>
                </tr>
              </thead>
              <tbody>
                {inds.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="muted">まだデータがありません</td>
                  </tr>
                ) : (
                  inds.map((r, i) => (
                    <tr key={i}>
                      <td className="mono">{fmt(r.created_at)}</td>
                      <td className="mono">{r.symbol}</td>
                      <td className="mono">{r.close}</td>
                      <td className="mono">{r.ema_fast ?? '-'}</td>
                      <td className="mono">{r.ema_slow ?? '-'}</td>
                      <td className="mono">{r.rsi ?? '-'}</td>
                      <td className="mono">{r.blog_ma_score ?? '-'}</td>
                      <td className="mono">{r.blog_rsi_score ?? '-'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
