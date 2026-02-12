export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../../_components/AutoReload';

type Row = {
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

  const rows = await sql<Row>(
    `
    SELECT created_at, symbol, interval, close, ema_fast, ema_slow, rsi, blog_ma_score, blog_rsi_score
    FROM binance_indicator_point
    ORDER BY created_at DESC
    LIMIT 200
    `
  );

  return (
    <main className="container">
      <AutoReload seconds={30} />
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">Binance 市場（指標）</div>
        <div className="muted">BTC/ETH 15分足の指標スナップショット（常に保存）</div>
        <div style={{ marginTop: 8 }}>
          <Link href="/">← 戻る</Link>
          <span className="muted"> ・ </span>
          <Link href="/binance/signals">シグナル</Link>
          <span className="muted"> ・ </span>
          <Link href="/binance/orders">注文</Link>
        </div>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>時刻</th>
              <th>銘柄</th>
              <th>足</th>
              <th>終値</th>
              <th>EMA fast</th>
              <th>EMA slow</th>
              <th>RSI</th>
              <th>記事MA</th>
              <th>記事RSI</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={9} className="muted">まだデータがありません（常駐が起動しているか確認してください）</td>
              </tr>
            ) : (
              rows.map((r, i) => (
                <tr key={i}>
                  <td className="mono">{fmt(r.created_at)}</td>
                  <td className="mono">{r.symbol}</td>
                  <td className="mono">{r.interval}</td>
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
    </main>
  );
}
