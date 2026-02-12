export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../_components/AutoReload';

function fmt(ts: any) {
  if (!ts) return '-';
  const s = ts instanceof Date ? ts.toISOString() : String(ts);
  return s.replace('T', ' ').replace('Z', '');
}

type SigRow = {
  created_at: any;
  source_key: string;
  item_id: string;
  score: number;
  label: string;
  tags: string[] | null;
  title: string | null;
  url: string | null;
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

  const sigs = await sql<SigRow>(
    `
    SELECT cs.created_at, cs.source_key, cs.item_id, cs.score, cs.label, cs.tags,
           ci.title, ci.url
    FROM content_signal cs
    JOIN content_item ci
      ON ci.source_key = cs.source_key AND ci.item_id = cs.item_id
    ORDER BY cs.created_at DESC
    LIMIT 200
    `
  );

  return (
    <main className="container">
      <AutoReload seconds={30} />
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">シグナル</div>
        <div className="muted">フェーズA：キーワードベースの強気シグナル（score{'≥'}2）。実売買はしない。</div>
        <div style={{ marginTop: 8 }}>
          <Link href="/">← Back</Link>
        </div>
      </div>

      <div className="card">
        <div style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>作成</th>
                <th>スコア</th>
                <th>ソース</th>
                <th>タグ</th>
                <th>タイトル</th>
              </tr>
            </thead>
            <tbody>
              {sigs.map((s, idx) => (
                <tr key={idx}>
                  <td>{fmt(s.created_at)}</td>
                  <td>{s.score}</td>
                  <td>{s.source_key}</td>
                  <td>{(s.tags && s.tags.length) ? s.tags.join(', ') : ''}</td>
                  <td>
                    {s.url ? (
                      <a href={s.url} target="_blank" rel="noreferrer" style={{ textDecoration: 'underline', textUnderlineOffset: 2 }}>
                        {s.title ?? s.url}
                      </a>
                    ) : (
                      s.title ?? ''
                    )}
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
