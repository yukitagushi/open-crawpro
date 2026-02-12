export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../../_components/AutoReload';

type Row = {
  created_at: any;
  symbol: string;
  side: string;
  status: string;
  quote_qty: number | null;
  base_qty: number | null;
  price: number | null;
  take_profit_price: number | null;
  stop_loss_price: number | null;
  stop_limit_price: number | null;
  oco_order_list_id: string | null;
  error: string | null;
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
    SELECT created_at, symbol, side, status, quote_qty, base_qty, price,
           take_profit_price, stop_loss_price, stop_limit_price, oco_order_list_id, error
    FROM binance_order
    ORDER BY created_at DESC
    LIMIT 200
    `
  );

  return (
    <main className="container">
      <AutoReload seconds={30} />
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">Binance 注文</div>
        <div className="muted">自動売買の注文ログ（根拠・利確/損切はDBに保存）</div>
        <div style={{ marginTop: 8 }}>
          <Link href="/">← 戻る</Link>
          <span className="muted"> ・ </span>
          <Link href="/binance/market">市場</Link>
          <span className="muted"> ・ </span>
          <Link href="/binance/market">市場/指標</Link>
          <span className="muted"> ・ </span>
          <Link href="/binance/signals">シグナル</Link>
        </div>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>時刻</th>
              <th>銘柄</th>
              <th>方向</th>
              <th>状態</th>
              <th>約定価格</th>
              <th>数量</th>
              <th>想定利確</th>
              <th>想定損切</th>
              <th>OCO</th>
              <th>エラー</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={10} className="muted">まだデータがありません</td>
              </tr>
            ) : (
              rows.map((r, i) => (
                <tr key={i}>
                  <td className="mono">{fmt(r.created_at)}</td>
                  <td className="mono">{r.symbol}</td>
                  <td className="mono">{r.side}</td>
                  <td>{r.status}</td>
                  <td className="mono">{r.price ?? '-'}</td>
                  <td className="mono">{r.base_qty ?? '-'}</td>
                  <td className="mono">{r.take_profit_price ?? '-'}</td>
                  <td className="mono">{r.stop_loss_price ?? '-'}</td>
                  <td className="mono">{r.oco_order_list_id ?? '-'}</td>
                  <td style={{ maxWidth: 420 }} className="muted">{r.error ?? ''}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
