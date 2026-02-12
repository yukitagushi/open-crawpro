'use client';

import { useMemo, useState } from 'react';

export type Row = {
  created_at: any;
  symbol: string;
  side: string;
  status: string;
  quote_qty: number | null;
  base_qty: number | null;
  price: number | null;
  take_profit_price: number | null;
  stop_loss_price: number | null;
  stop_limit_price: number | null;
  oco_order_list_id: string | null;
  error: string | null;
};

function fmt(ts: any) {
  if (!ts) return '-';
  const s = ts instanceof Date ? ts.toISOString() : String(ts);
  return s.replace('T', ' ').replace('Z', '');
}

export function OrdersTable({ rows }: { rows: Row[] }) {
  const [showErrors, setShowErrors] = useState(false);

  const filtered = useMemo(() => {
    if (showErrors) return rows;
    return rows.filter((r) => r.status !== 'error');
  }, [rows, showErrors]);

  return (
    <>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 10 }}>
        <div className="muted" style={{ flex: 1 }}>
          表示件数: {filtered.length} / {rows.length}
        </div>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input type="checkbox" checked={showErrors} onChange={(e) => setShowErrors(e.target.checked)} />
          <span>エラーも表示</span>
        </label>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>時刻</th>
            <th>銘柄</th>
            <th>方向</th>
            <th>状態</th>
            <th>約定価格</th>
            <th>数量</th>
            <th>想定利確</th>
            <th>想定損切</th>
            <th>OCO</th>
            <th>エラー</th>
          </tr>
        </thead>
        <tbody>
          {filtered.length === 0 ? (
            <tr>
              <td colSpan={10} className="muted">表示できるデータがありません（エラー非表示中）</td>
            </tr>
          ) : (
            filtered.map((r, i) => (
              <tr key={i}>
                <td className="mono">{fmt(r.created_at)}</td>
                <td className="mono">{r.symbol}</td>
                <td className="mono">{r.side}</td>
                <td>{r.status}</td>
                <td className="mono">{r.price ?? '-'}</td>
                <td className="mono">{r.base_qty ?? '-'}</td>
                <td className="mono">{r.take_profit_price ?? '-'}</td>
                <td className="mono">{r.stop_loss_price ?? '-'}</td>
                <td className="mono">{r.oco_order_list_id ?? '-'}</td>
                <td style={{ maxWidth: 420 }} className="muted">{r.error ?? ''}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </>
  );
}
