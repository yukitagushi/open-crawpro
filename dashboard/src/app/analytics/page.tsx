export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../_components/AutoReload';

type TagAggRow = { tag: string; cnt: number };

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

  // Top tags in last 24h of fetched content
  const topTags24h = await sql<TagAggRow>(
    `
    SELECT t.tag, COUNT(*)::int as cnt
    FROM (
      SELECT unnest(COALESCE(tags, ARRAY[]::text[])) as tag
      FROM content_item
      WHERE fetched_at >= now() - interval '24 hours'
    ) t
    GROUP BY t.tag
    ORDER BY cnt DESC
    LIMIT 20
    `
  );

  // Top tags among bullish signals
  const topTagsSignals = await sql<TagAggRow>(
    `
    SELECT t.tag, COUNT(*)::int as cnt
    FROM (
      SELECT unnest(COALESCE(tags, ARRAY[]::text[])) as tag
      FROM content_signal
      WHERE label='bullish'
      AND created_at >= now() - interval '7 days'
    ) t
    GROUP BY t.tag
    ORDER BY cnt DESC
    LIMIT 20
    `
  );

  return (
    <main className="container">
      <AutoReload seconds={30} />
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">分析</div>
        <div className="muted">収集記事/シグナルのタグ集計（どんな指標・テーマが多いか）</div>
        <div style={{ marginTop: 8 }}>
          <Link href="/">← 戻る</Link>
        </div>
      </div>

      <div className="grid">
        <div className="card" style={{ gridColumn: 'span 6' }}>
          <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>直近24h：よく出るタグ</div>
          <div className="muted">content_item.tags 集計</div>
          <div style={{ marginTop: 10 }}>
            {topTags24h.length === 0 ? (
              <div className="muted">まだタグがありません（次の実行で付与されます）</div>
            ) : (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {topTags24h.map((r) => (
                  <li key={r.tag}>
                    {r.tag} — {r.cnt}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="card" style={{ gridColumn: 'span 6' }}>
          <div style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>直近7日：強気シグナルに多いタグ</div>
          <div className="muted">content_signal.tags 集計</div>
          <div style={{ marginTop: 10 }}>
            {topTagsSignals.length === 0 ? (
              <div className="muted">まだシグナルがありません</div>
            ) : (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {topTagsSignals.map((r) => (
                  <li key={r.tag}>
                    {r.tag} — {r.cnt}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
