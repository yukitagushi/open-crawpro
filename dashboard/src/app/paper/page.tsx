export const dynamic = 'force-dynamic';

import { hasDatabase, sql } from '@/lib/db';

function fmt(ts: any) {
  if (!ts) return '-';
  const s = ts instanceof Date ? ts.toISOString() : String(ts);
  return s.replace('T', ' ').replace('Z', '');
}

export default async function PaperPage() {
  if (!hasDatabase()) {
    return (
      <main className="container">
        <div className="card">
          <div className="h1">Setup required</div>
          <div className="muted">DATABASE_URL を Vercel に設定してください。</div>
        </div>
      </main>
    );
  }

  // aggregate
  const agg = await sql<{ fills: number; notional: number }>(
    `
    SELECT
      COUNT(*)::int as fills,
      COALESCE(SUM(price * size), 0)::float8 as notional
    FROM paper_fills
    `
  );
  const fills = agg?.[0]?.fills ?? 0;
  const notional = agg?.[0]?.notional ?? 0;

  // latest fills
  const rows = await sql<{ created_at: any; side: string; condition_id: string | null; token_id: string | null; price: number; size: number }>(
    `
    SELECT created_at, side, condition_id, token_id, price, size
    FROM paper_fills
    ORDER BY created_at DESC
    LIMIT 200
    `
  );

  // NOTE: true PnL requires exits/marks; for now show spending/notional and fill counts.
  // We'll add mark-to-market once we store mark prices or use orderbook mid.

  return (
    <main className="container">
      <div className="grid" style={{ marginBottom: 12 }}>
        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div className="h1">Paper Trading</div>
          <div className="muted">バーチャルトレード（擬似約定）履歴。まずは回数と想定購入額を表示します。</div>
        </div>

        <div className="card" style={{ gridColumn: 'span 4' }}>
          <div className="kpi">{fills}</div>
          <div className="kpiLabel">paper fills</div>
        </div>
        <div className="card" style={{ gridColumn: 'span 4' }}>
          <div className="kpi">${notional.toFixed(2)}</div>
          <div className="kpiLabel">total notional (buy/sell)</div>
        </div>
        <div className="card" style={{ gridColumn: 'span 4' }}>
          <div className="kpi">-</div>
          <div className="kpiLabel">PnL (next)</div>
        </div>

        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>Paper fills</div>
            <div className="muted">created / market_id / side / price / size</div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>created</th>
                  <th>market_id</th>
                  <th>side</th>
                  <th>price</th>
                  <th>size</th>
                  <th>notional</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    <td>{fmt(r.created_at)}</td>
                    <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                      {r.condition_id ?? ''}
                    </td>
                    <td>{r.side}</td>
                    <td>{Number(r.price).toFixed(4)}</td>
                    <td>{Number(r.size).toFixed(4)}</td>
                    <td>${(Number(r.price) * Number(r.size)).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="muted">
        次：paper_position_snapshot（平均取得単価）+ orderbook mid で評価して、PnL/勝率を出します。
      </div>
    </main>
  );
}
