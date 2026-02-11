export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';

function fmt(ts: any) {
  if (!ts) return '-';
  const s = ts instanceof Date ? ts.toISOString() : String(ts);
  return s.replace('T', ' ').replace('Z', '');
}

type PaperFillRow = {
  created_at: any;
  paper_fill_id: string;
  client_order_id: string | null;
  condition_id: string | null;
  token_id: string | null;
  side: string;
  price: number;
  size: number;
};

type PaperPosRow = {
  snapshot_at: any;
  token_id: string | null;
  position_size: number;
  avg_entry_price: number | null;
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

  const fills = await sql<PaperFillRow>(
    `
    SELECT created_at, paper_fill_id, client_order_id, condition_id, token_id, side, price, size
    FROM paper_fills
    ORDER BY created_at DESC
    LIMIT 200
    `
  );

  const pos = await sql<PaperPosRow>(
    `
    SELECT snapshot_at, token_id, position_size, avg_entry_price
    FROM paper_position_snapshot
    ORDER BY snapshot_at DESC
    LIMIT 50
    `
  );

  return (
    <main className="container">
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">Paper trade</div>
        <div className="muted">仮想約定（シミュレーション）と仮想ポジションのログ。</div>
        <div style={{ marginTop: 8 }}>
          <Link href="/">← Back</Link>
        </div>
      </div>

      <div className="grid" style={{ marginBottom: 12 }}>
        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>Paper position snapshots</div>
          <div className="muted">token / position_size / avg_entry_price</div>
          <div style={{ overflowX: 'auto', marginTop: 8 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>snapshot</th>
                  <th>token_id</th>
                  <th>position_size</th>
                  <th>avg_entry</th>
                </tr>
              </thead>
              <tbody>
                {pos.map((p, i) => (
                  <tr key={i}>
                    <td>{fmt(p.snapshot_at)}</td>
                    <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                      {p.token_id ?? ''}
                    </td>
                    <td>{Number(p.position_size).toFixed(4)}</td>
                    <td>{p.avg_entry_price == null ? '' : Number(p.avg_entry_price).toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>Paper fills</div>
          <div className="muted">paper_fill_id / side / price / size</div>
          <div style={{ overflowX: 'auto', marginTop: 8 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>created</th>
                  <th>side</th>
                  <th>price</th>
                  <th>size</th>
                  <th>condition_id</th>
                  <th>token_id</th>
                  <th>paper_fill_id</th>
                </tr>
              </thead>
              <tbody>
                {fills.map((f) => (
                  <tr key={f.paper_fill_id}>
                    <td>{fmt(f.created_at)}</td>
                    <td>{f.side}</td>
                    <td>{Number(f.price).toFixed(4)}</td>
                    <td>{Number(f.size).toFixed(4)}</td>
                    <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                      {f.condition_id ?? ''}
                    </td>
                    <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                      {f.token_id ?? ''}
                    </td>
                    <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                      {f.paper_fill_id}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
