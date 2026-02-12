export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../../_components/AutoReload';
import { OrdersTable, type Row } from './client';

export default async function Page({
  searchParams,
}: {
  searchParams?: { page?: string; pageSize?: string; order?: string; showErrors?: string };
}) {
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

  const pageSize = Math.max(5, Math.min(100, parseInt(searchParams?.pageSize || '10', 10) || 10));
  const page = Math.max(0, parseInt(searchParams?.page || '0', 10) || 0);
  const order = (searchParams?.order || 'desc').toLowerCase() === 'asc' ? 'asc' : 'desc';

  const offset = page * pageSize;

  const rows = await sql<Row>(
    `
    SELECT created_at, symbol, side, status, quote_qty, base_qty, price,
           take_profit_price, stop_loss_price, stop_limit_price, oco_order_list_id, error
    FROM binance_order
    ORDER BY created_at ${order === 'asc' ? 'ASC' : 'DESC'}
    LIMIT ${pageSize}
    OFFSET ${offset}
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
          <Link href="/binance/market">市場/指標</Link>
          <span className="muted"> ・ </span>
          <Link href="/binance/signals">シグナル</Link>
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 10, flexWrap: 'wrap' }}>
          <div className="muted">page: {page + 1} / size: {pageSize} / order: {order.toUpperCase()}</div>
          <Link className="toplink" href={`/binance/orders?page=${Math.max(0, page - 1)}&pageSize=${pageSize}&order=${order}`}>
            ← Prev
          </Link>
          <Link className="toplink" href={`/binance/orders?page=${page + 1}&pageSize=${pageSize}&order=${order}`}>
            Next →
          </Link>
          <Link className="toplink" href={`/binance/orders?page=0&pageSize=${pageSize}&order=${order === 'asc' ? 'desc' : 'asc'}`}>
            並び替え: {order === 'asc' ? '新→古' : '古→新'}
          </Link>
        </div>
      </div>

      <div className="card">
        <OrdersTable rows={rows} />
      </div>
    </main>
  );
}
