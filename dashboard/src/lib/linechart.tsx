import React from 'react';

export function LineChart({ values, width = 520, height = 120 }: { values: number[]; width?: number; height?: number }) {
  if (!values || values.length < 2) {
    return <div className="muted">データ不足</div>;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(1e-9, max - min);

  const pad = 6;
  const w = width;
  const h = height;

  const pts = values
    .map((v, i) => {
      const x = pad + (i * (w - pad * 2)) / (values.length - 1);
      const y = pad + (1 - (v - min) / span) * (h - pad * 2);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label="line chart">
      <rect x={0} y={0} width={w} height={h} rx={12} fill="rgba(16,163,127,0.03)" stroke="rgba(17,24,39,0.10)" />
      <polyline fill="none" stroke="#10A37F" strokeWidth={2} points={pts} />
    </svg>
  );
}
