export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../_components/AutoReload';

function fmt(ts: any) {
  if (!ts) return '-';
  const s = ts instanceof Date ? ts.toISOString() : String(ts);
  return s.replace('T', ' ').replace('Z', '');
}

type FillRow = {
  created_at: any;
  fill_id: string;
  order_id: string | null;
  condition_id: string | null;
  token_id: string | null;
  side: string;
  price: number;
  size: number;
  fee: number | null;
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

  const fills = await sql<FillRow>(
    `
    SELECT created_at, fill_id, order_id, condition_id, token_id, side, price, size, fee
    FROM fills
    ORDER BY created_at DESC
    LIMIT 200
    `
  );

  return (
    <main className="container">
      <AutoReload seconds={30} />
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">約定（取引実績）</div>
        <div className="muted">最新200件。Polymarketの取引実績（get_trades）由来。</div>
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
                <th>side</th>
                <th>price</th>
                <th>size</th>
                <th>fee</th>
                <th>condition_id</th>
                <th>token_id</th>
                <th>fill_id</th>
              </tr>
            </thead>
            <tbody>
              {fills.map((f) => (
                <tr key={f.fill_id}>
                  <td>{fmt(f.created_at)}</td>
                  <td>{f.side}</td>
                  <td>{Number(f.price).toFixed(4)}</td>
                  <td>{Number(f.size).toFixed(4)}</td>
                  <td>{f.fee == null ? '' : Number(f.fee).toFixed(6)}</td>
                  <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                    {f.condition_id ?? ''}
                  </td>
                  <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                    {f.token_id ?? ''}
                  </td>
                  <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                    {f.fill_id}
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
