export const dynamic = 'force-dynamic';

import { hasDatabase, sql } from '@/lib/db';
import { Sparkline } from '@/lib/sparkline';

type BotRunRow = {
  started_at: string;
  finished_at: string | null;
  status: string;
  discovered_count: number | null;
  error: string | null;
};

type DiscoveredRow = {
  last_seen_at: string;
  seen_count: number;
  market_id: string;
  question: string | null;
  yes_token_id: string | null;
  no_token_id: string | null;
};

function fmt(ts: any) {
  if (!ts) return '-';
  // pg can return Date objects for timestamptz
  const s = ts instanceof Date ? ts.toISOString() : String(ts);
  return s.replace('T', ' ').replace('Z', '');
}

export default async function Page() {
  if (!hasDatabase()) {
    return (
      <main className="container">
        <div className="card">
          <div className="h1">Setup required</div>
          <div className="muted" style={{ marginBottom: 12 }}>
            DATABASE_URL が未設定のため、DBに接続できません。Vercel の Environment Variables に DATABASE_URL を追加してください。
          </div>
          <div className="card" style={{ background: 'var(--panel)' }}>
            <div style={{ fontWeight: 800 }}>Vercel → Project → Settings → Environment Variables</div>
            <div className="muted">Key: DATABASE_URL / Value: Neonの postgresql://... </div>
          </div>
        </div>
      </main>
    );
  }

  const runs = await sql<BotRunRow>(
    `
    SELECT started_at, finished_at, status, discovered_count, error
    FROM bot_run
    ORDER BY started_at DESC
    LIMIT 50
    `
  );

  const markets = await sql<DiscoveredRow>(
    `
    SELECT last_seen_at, seen_count, market_id, question, yes_token_id, no_token_id
    FROM discovered_market
    ORDER BY last_seen_at DESC
    LIMIT 50
    `
  );

  const okCount = runs.filter((r) => r.status === 'ok').length;
  const latest = runs[0]?.started_at ?? null;
  const discoveredSeries = runs
    .slice()
    .reverse()
    .map((r) => (typeof r.discovered_count === 'number' ? r.discovered_count : 0));

  // trades (fills)
  const fillAgg = await sql<{ fills: number }>(`SELECT COUNT(*)::int as fills FROM fills`);
  const fillsCount = fillAgg?.[0]?.fills ?? 0;

  return (
    <main className="container">
      <div className="grid" style={{ marginBottom: 12 }}>
        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div className="h1">Overview</div>
          <div className="muted">白ベースで、実行状況とデータを確認できます（PnLは次の段階で追加）。</div>
        </div>

        <div className="card" style={{ gridColumn: 'span 4' }}>
          <div className="kpi">{runs.length}</div>
          <div className="kpiLabel">runs (last 50)</div>
        </div>
        <div className="card" style={{ gridColumn: 'span 4' }}>
          <div className="kpi">{okCount}</div>
          <div className="kpiLabel">ok</div>
        </div>
        <div className="card" style={{ gridColumn: 'span 4' }}>
          <div className="kpi">{latest ? fmt(latest) : '-'}</div>
          <div className="kpiLabel">latest run</div>
        </div>

        <div className="card" style={{ gridColumn: 'span 4' }}>
          <div className="kpi">{fillsCount}</div>
          <div className="kpiLabel">fills (trades)</div>
        </div>

        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>Discovery count (sparkline)</div>
              <div className="muted">bot_run.discovered_count の推移</div>
            </div>
            <Sparkline values={discoveredSeries} />
          </div>
        </div>

        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>Runs</div>
            <div className="muted">status / discovered_count / error</div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>started</th>
                  <th>status</th>
                  <th>discovered</th>
                  <th>error</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r, i) => (
                  <tr key={i}>
                    <td>{fmt(r.started_at)}</td>
                    <td>
                      {r.status === 'ok' ? (
                        <span className="pill-ok"><span className="dot" /> OK</span>
                      ) : (
                        <span className="pill-bad"><span style={{ width: 8, height: 8, borderRadius: 999, background: '#EF4444', display: 'inline-block' }} /> {r.status}</span>
                      )}
                    </td>
                    <td>{r.discovered_count ?? '-'}</td>
                    <td style={{ maxWidth: 520, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.error ?? ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>Discovered markets</div>
            <div className="muted">last_seen / seen_count / market_id</div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>last_seen</th>
                  <th>seen</th>
                  <th>question</th>
                  <th>market_id</th>
                </tr>
              </thead>
              <tbody>
                {markets.map((m) => (
                  <tr key={m.market_id}>
                    <td>{fmt(m.last_seen_at)}</td>
                    <td>{m.seen_count}</td>
                    <td style={{ maxWidth: 520 }}>{m.question ?? ''}</td>
                    <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                      {m.market_id}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="muted">
        次：fills / position_snapshot をDBに保存 → PnL/勝率/累積損益をこのダッシュボードに追加します。
      </div>
    </main>
  );
}
