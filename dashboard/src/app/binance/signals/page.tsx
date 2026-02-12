export const dynamic = 'force-dynamic';

import Link from 'next/link';
import { hasDatabase, sql } from '@/lib/db';
import { AutoReload } from '../../_components/AutoReload';

type Row = {
  created_at: any;
  symbol: string;
  kind: string;
  score: number;
  evidence_json: any;
};

function fmt(ts: any) {
  if (!ts) return '-';
  const s = ts instanceof Date ? ts.toISOString() : String(ts);
  return s.replace('T', ' ').replace('Z', '');
}

export default async function Page({
  searchParams,
}: {
  searchParams?: { page?: string; pageSize?: string; order?: string };
}) {
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

  const pageSize = Math.max(5, Math.min(100, parseInt(searchParams?.pageSize || '10', 10) || 10));
  const page = Math.max(0, parseInt(searchParams?.page || '0', 10) || 0);
  const order = (searchParams?.order || 'desc').toLowerCase() === 'asc' ? 'asc' : 'desc';
  const offset = page * pageSize;

  const rows = await sql<Row>(
    `
    SELECT created_at, symbol, kind, score, evidence_json
    FROM binance_signal
    ORDER BY created_at ${order === 'asc' ? 'ASC' : 'DESC'}
    LIMIT ${pageSize}
    OFFSET ${offset}
    `
  );

  return (
    <main className="container">
      <AutoReload seconds={30} />
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="h1">Binance シグナル</div>
        <div className="muted">なぜ買い候補になったかの根拠ログ</div>
        <div style={{ marginTop: 8 }}>
          <Link href="/">← 戻る</Link>
          <span className="muted"> ・ </span>
          <Link href="/binance/market">市場/指標</Link>
          <span className="muted"> ・ </span>
          <Link href="/binance/orders">注文</Link>
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 10, flexWrap: 'wrap' }}>
          <div className="muted">page: {page + 1} / size: {pageSize} / order: {order.toUpperCase()}</div>
          <Link className="toplink" href={`/binance/signals?page=${Math.max(0, page - 1)}&pageSize=${pageSize}&order=${order}`}>
            ← Prev
          </Link>
          <Link className="toplink" href={`/binance/signals?page=${page + 1}&pageSize=${pageSize}&order=${order}`}>
            Next →
          </Link>
          <Link className="toplink" href={`/binance/signals?page=0&pageSize=${pageSize}&order=${order === 'asc' ? 'desc' : 'asc'}`}>
            並び替え: {order === 'asc' ? '新→古' : '古→新'}
          </Link>
        </div>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>時刻</th>
              <th>銘柄</th>
              <th>種別</th>
              <th>スコア</th>
              <th>根拠</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="muted">まだデータがありません</td>
              </tr>
            ) : (
              rows.map((r, i) => (
                <tr key={i}>
                  <td className="mono">{fmt(r.created_at)}</td>
                  <td className="mono">{r.symbol}</td>
                  <td className="mono">{r.kind}</td>
                  <td className="mono">{r.score.toFixed(3)}</td>
                  <td>
                    <details>
                      <summary className="muted">表示</summary>
                      <pre className="pre">{JSON.stringify(r.evidence_json, null, 2)}</pre>
                    </details>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
