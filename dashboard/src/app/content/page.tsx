export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../_components/AutoReload';

function fmt(ts: any) {
  if (!ts) return '-';
  const s = ts instanceof Date ? ts.toISOString() : String(ts);
  return s.replace('T', ' ').replace('Z', '');
}

type ItemRow = {
  fetched_at: any;
  published_at: any;
  source_key: string;
  title: string | null;
  url: string | null;
  injection_detected: boolean;
  injection_excerpt: string | null;
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

  const items = await sql<ItemRow>(
    `
    SELECT fetched_at, published_at, source_key, title, url, injection_detected, injection_excerpt
    FROM content_item
    ORDER BY fetched_at DESC
    LIMIT 200
    `
  );

  const flagged = items.filter((i) => i.injection_detected).length;

  return (
    <main className="container">
      <AutoReload seconds={30} />
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">収集記事</div>
        <div className="muted">RSS/ブログ等の収集ログ（最新200件）。Injection検知は要注意としてフラグ付け。</div>
        <div className="muted" style={{ marginTop: 6 }}>flagged: {flagged}</div>
        <div style={{ marginTop: 8 }}>
          <Link href="/">← Back</Link>
        </div>
      </div>

      <div className="card">
        <div style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>fetched</th>
                <th>published</th>
                <th>source</th>
                <th>title</th>
                <th>flag</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, idx) => (
                <tr key={idx}>
                  <td>{fmt(it.fetched_at)}</td>
                  <td>{fmt(it.published_at)}</td>
                  <td>{it.source_key}</td>
                  <td>
                    {it.url ? (
                      <a href={it.url} target="_blank" rel="noreferrer" style={{ textDecoration: 'underline', textUnderlineOffset: 2 }}>
                        {it.title ?? it.url}
                      </a>
                    ) : (
                      it.title ?? ''
                    )}
                    {it.injection_detected && it.injection_excerpt ? (
                      <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
                        injection_excerpt: {it.injection_excerpt}
                      </div>
                    ) : null}
                  </td>
                  <td>{it.injection_detected ? '⚠️' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
