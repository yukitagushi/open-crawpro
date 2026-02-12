export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../../_components/AutoReload';

type Agg = {
  closed: number;
  pnl_sum: number;
  pnl_avg: number;
  win_rate: number;
};

type Row = {
  created_at: any;
  symbol: string;
  status: string;
  entry_quote_qty: number | null;
  exit_quote_qty: number | null;
  pnl_quote: number | null;
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

  const agg = await sql<Agg>(
    `
    SELECT
      COUNT(*)::int as closed,
      COALESCE(SUM(pnl_quote),0)::float8 as pnl_sum,
      COALESCE(AVG(pnl_quote),0)::float8 as pnl_avg,
      COALESCE(AVG(CASE WHEN pnl_quote > 0 THEN 1 ELSE 0 END),0)::float8 as win_rate
    FROM binance_position
    WHERE status='closed'
    `
  );

  const a = agg?.[0] || { closed: 0, pnl_sum: 0, pnl_avg: 0, win_rate: 0 };

  const rows = await sql<Row>(
    `
    SELECT created_at, symbol, status, entry_quote_qty, exit_quote_qty, pnl_quote
    FROM binance_position
    ORDER BY created_at DESC
    LIMIT 200
    `
  );

  return (
    <main className="container">
      <AutoReload seconds={30} />

      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">Binance 収益</div>
        <div className="muted">binance_position の損益（pnl_quote）集計</div>
        <div style={{ marginTop: 8 }}>
          <Link href="/binance/market">市場/指標</Link>
          <span className="muted"> ・ </span>
          <Link href="/binance/orders">注文</Link>
          <span className="muted"> ・ </span>
          <Link href="/binance/signals">シグナル</Link>
        </div>
      </div>

      <div className="grid">
        <div className="card" style={{ gridColumn: 'span 6' }}>
          <div style={{ fontWeight: 800 }}>累計損益（USDT）</div>
          <div className="h1 mono" style={{ marginTop: 6 }}>{a.pnl_sum.toFixed(4)}</div>
          <div className="muted">closed: {a.closed}</div>
        </div>
        <div className="card" style={{ gridColumn: 'span 6' }}>
          <div style={{ fontWeight: 800 }}>平均損益 / 勝率</div>
          <div className="mono" style={{ marginTop: 6 }}>avg: {a.pnl_avg.toFixed(6)}</div>
          <div className="mono">win rate: {(a.win_rate * 100).toFixed(1)}%</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div style={{ fontWeight: 800, marginBottom: 8 }}>直近ポジション</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>時刻</th>
                <th>銘柄</th>
                <th>状態</th>
                <th>エントリー</th>
                <th>エグジット</th>
                <th>PnL</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="muted">まだデータがありません</td>
                </tr>
              ) : (
                rows.map((r, i) => (
                  <tr key={i}>
                    <td className="mono">{fmt(r.created_at)}</td>
                    <td className="mono">{r.symbol}</td>
                    <td>{r.status}</td>
                    <td className="mono">{r.entry_quote_qty ?? '-'}</td>
                    <td className="mono">{r.exit_quote_qty ?? '-'}</td>
                    <td className="mono">{r.pnl_quote ?? '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
