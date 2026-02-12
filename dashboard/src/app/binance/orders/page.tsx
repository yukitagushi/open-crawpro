export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../../_components/AutoReload';
import { OrdersTable, type Row } from './client';

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
        <OrdersTable rows={rows} />
      </div>
    </main>
  );
}
