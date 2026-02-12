export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { LineChart } from '@/lib/linechart';
import { AutoReload } from '../_components/AutoReload';

function fmt(ts: any) {
  if (!ts) return '-';
  const s = ts instanceof Date ? ts.toISOString() : String(ts);
  return s.replace('T', ' ').replace('Z', '');
}

type Row = {
  snapshot_at: any;
  mid: number | null;
  position_size: number;
  avg_entry_price: number | null;
  unrealized_pnl: number | null;
};

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
    SELECT snapshot_at, mid, position_size, avg_entry_price, unrealized_pnl
    FROM paper_pnl_point
    ORDER BY snapshot_at DESC
    LIMIT 300
    `
  );

  const series = rows
    .slice()
    .reverse()
    .map((r) => (typeof r.unrealized_pnl === 'number' ? r.unrealized_pnl : 0));

  const latest = rows[0] ?? null;

  return (
    <main className="container">
      <AutoReload seconds={30} />
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">収益（ペーパー）</div>
        <div className="muted">紙トレードの含み損益（midで評価）。</div>
        <div style={{ marginTop: 8 }}>
          <Link href="/">← 戻る</Link>
        </div>
      </div>

      <div className="grid" style={{ marginBottom: 12 }}>
        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>含み損益の推移</div>
            <div className="muted">直近{Math.min(300, rows.length)}点</div>
          </div>
          <div style={{ marginTop: 10 }}>
            <LineChart values={series} width={900} height={180} />
          </div>
        </div>

        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>最新</div>
          <div className="muted" style={{ marginTop: 6 }}>
            {latest ? (
              <>
                時刻: {fmt((latest as any).snapshot_at)} / mid: {latest.mid ?? '-'} / position: {Number(latest.position_size).toFixed(4)} / avg: {latest.avg_entry_price ?? '-'} / pnl: {latest.unrealized_pnl ?? '-'}
              </>
            ) : (
              'データなし'
            )}
          </div>
        </div>

        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>履歴</div>
          <div className="muted">snapshot / mid / position / avg / unrealized_pnl</div>
          <div style={{ overflowX: 'auto', marginTop: 8 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>時刻</th>
                  <th>mid</th>
                  <th>pos</th>
                  <th>avg</th>
                  <th>pnl</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 50).map((r, i) => (
                  <tr key={i}>
                    <td>{fmt(r.snapshot_at)}</td>
                    <td>{r.mid == null ? '' : Number(r.mid).toFixed(4)}</td>
                    <td>{Number(r.position_size).toFixed(4)}</td>
                    <td>{r.avg_entry_price == null ? '' : Number(r.avg_entry_price).toFixed(4)}</td>
                    <td>{r.unrealized_pnl == null ? '' : Number(r.unrealized_pnl).toFixed(4)}</td>
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
