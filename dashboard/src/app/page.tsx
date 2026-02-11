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

  // bot_run columns can evolve; keep dashboard resilient even if migrations lag behind.
  const cols = await sql<{ column_name: string }>(
    `
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='bot_run'
    `
  );
  const colset = new Set(cols.map((c) => c.column_name));
  const opt = (name: string, cast: string) => (colset.has(name) ? name : `NULL::${cast} AS ${name}`);

  const runs = await sql<
    BotRunRow & {
      trades_fetched?: number | null;
      fills_inserted?: number | null;
      dry_run?: boolean | null;
      max_notional_usd?: number | null;
      max_price?: number | null;
      paper_plans_count?: number | null;
      paper_fills_inserted?: number | null;
    }
  >(
    `
    SELECT
      started_at,
      finished_at,
      status,
      discovered_count,
      ${opt('trades_fetched', 'int')},
      ${opt('fills_inserted', 'int')},
      ${opt('dry_run', 'bool')},
      ${opt('max_notional_usd', 'float8')},
      ${opt('max_price', 'float8')},
      ${opt('paper_plans_count', 'int')},
      ${opt('paper_fills_inserted', 'int')},
      error
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
  const latestAgeMin = (() => {
    if (!latest) return null;
    const d = new Date(String(latest));
    const ms = Date.now() - d.getTime();
    if (!Number.isFinite(ms)) return null;
    return Math.max(0, Math.round(ms / 60000));
  })();
  const discoveredSeries = runs
    .slice()
    .reverse()
    .map((r) => (typeof r.discovered_count === 'number' ? r.discovered_count : 0));

  // trades (fills)
  const fillAgg = await sql<{ fills: number }>(`SELECT COUNT(*)::int as fills FROM fills`);
  const fillsCount = fillAgg?.[0]?.fills ?? 0;

  // planned / dry-run orders
  const plans = await sql<{ created_at: any; status: string; condition_id: string | null; token_id: string | null; side: string; price: number; size: number }>(
    `
    SELECT created_at, status, condition_id, token_id, side, price, size
    FROM orders
    WHERE status IN ('dry_run','submitted')
    ORDER BY created_at DESC
    LIMIT 20
    `
  );

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
          <div className="kpiLabel">latest run{latestAgeMin != null ? ` (${latestAgeMin} min ago)` : ''}</div>
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
            <div className="muted">status / discovered_count / dry_run / limits / error</div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>started</th>
                  <th>status</th>
                  <th>discovered</th>
                  <th>dry_run</th>
                  <th>max_notional</th>
                  <th>max_price</th>
                  <th>trades_fetched</th>
                  <th>fills_inserted</th>
                  <th>paper_plans</th>
                  <th>paper_fills+</th>
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
                    <td>{(r as any).dry_run == null ? '-' : String((r as any).dry_run)}</td>
                    <td>{(r as any).max_notional_usd == null ? '-' : Number((r as any).max_notional_usd).toFixed(2)}</td>
                    <td>{(r as any).max_price == null ? '-' : Number((r as any).max_price).toFixed(4)}</td>
                    <td>{(r as any).trades_fetched ?? '-'}</td>
                    <td>{(r as any).fills_inserted ?? '-'}</td>
                    <td>{(r as any).paper_plans_count ?? '-'}</td>
                    <td>{(r as any).paper_fills_inserted ?? '-'}</td>
                    <td style={{ maxWidth: 520, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.error ?? ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card" style={{ gridColumn: 'span 12' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>Planned orders (DRY_RUN)</div>
            <div className="muted">created / status / market_id / side / price / size</div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>created</th>
                  <th>status</th>
                  <th>market_id</th>
                  <th>side</th>
                  <th>price</th>
                  <th>size</th>
                </tr>
              </thead>
              <tbody>
                {plans.map((p, i) => (
                  <tr key={i}>
                    <td>{fmt(p.created_at)}</td>
                    <td>{p.status === 'dry_run' ? <span className="pill-ok"><span className="dot" /> DRY_RUN</span> : p.status}</td>
                    <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace', fontSize: 12 }}>
                      {p.condition_id ?? ''}
                    </td>
                    <td>{p.side}</td>
                    <td>{Number(p.price).toFixed(4)}</td>
                    <td>{Number(p.size).toFixed(4)}</td>
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
