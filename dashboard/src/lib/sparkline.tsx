import React from 'react';

export function Sparkline({ values, width = 240, height = 44 }: { values: number[]; width?: number; height?: number }) {
  if (!values.length) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(1e-9, max - min);

  const pad = 4;
  const w = width - pad * 2;
  const h = height - pad * 2;

  const pts = values.map((v, i) => {
    const x = pad + (i / Math.max(1, values.length - 1)) * w;
    const y = pad + (1 - (v - min) / range) * h;
    return [x, y] as const;
  });

  const d = pts
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`)
    .join(' ');

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="sparkline">
      <defs>
        <linearGradient id="ocGrad" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#10A37F" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#10A37F" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={d} fill="none" stroke="#10A37F" strokeWidth="2" strokeLinecap="round" />
      {/* simple area */}
      <path d={`${d} L ${pts[pts.length - 1][0].toFixed(2)} ${(height - 4).toFixed(2)} L ${pts[0][0].toFixed(2)} ${(height - 4).toFixed(2)} Z`} fill="url(#ocGrad)" />
    </svg>
  );
}
