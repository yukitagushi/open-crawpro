export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../_components/AutoReload';

function fmt(ts: any) {
  if (!ts) return '-';
  const s = ts instanceof Date ? ts.toISOString() : String(ts);
  return s.replace('T', ' ').replace('Z', '');
}

type OrderRow = {
  created_at: any;
  client_order_id: string;
  condition_id: string | null;
  token_id: string | null;
  side: string;
  price: number;
  size: number;
  status: string;
};

export default async function Page() {
  if (!hasDatabase()) {
    return (
      <main className="container">
        <div className="card">
          <div className="h1">Setup required</div>
          <div className="muted">DATABASE_URL が未設定のため、DBに接続できません。</div>
          <div style={{ marginTop: 12 }}>
            <Link href="/">← Back</Link>
          </div>
        </div>
      </main>
    );
  }

  const orders = await sql<OrderRow>(
    `
    SELECT created_at, client_order_id, condition_id, token_id, side, price, size, status
    FROM orders
    ORDER BY created_at DESC
    LIMIT 200
    `
  );

  return (
    <main className="container">
      <AutoReload seconds={30} />
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">注文</div>
        <div className="muted">最新200件。今はDRY_RUN計画注文もここに入ります。</div>
        <div style={{ marginTop: 8 }}>
          <Link href="/">← Back</Link>
        </div>
      </div>

      <div className="card">
        <div style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>created</th>
                <th>status</th>
                <th>side</th>
                <th>price</th>
                <th>size</th>
                <th>condition_id</th>
                <th>token_id</th>
                <th>client_order_id</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.client_order_id}>
                  <td>{fmt(o.created_at)}</td>
                  <td>{o.status}</td>
                  <td>{o.side}</td>
                  <td>{Number(o.price).toFixed(4)}</td>
                  <td>{Number(o.size).toFixed(4)}</td>
                  <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                    {o.condition_id ?? ''}
                  </td>
                  <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                    {o.token_id ?? ''}
                  </td>
                  <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                    {o.client_order_id}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
