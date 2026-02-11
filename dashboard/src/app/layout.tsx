import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Polymarket Bot Dashboard',
  description: 'Open-crawpro dashboard',
};

import Link from 'next/link';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <div className="topbar">
          <div className="topbar-inner">
            <div className="brand">
              <span style={{ width: 10, height: 10, borderRadius: 999, background: 'var(--primary)', display: 'inline-block' }} />
              Polymarket Bot Dashboard
            </div>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
              <Link href="/" className="toplink">Overview</Link>
              <Link href="/orders" className="toplink">Orders</Link>
              <Link href="/fills" className="toplink">Fills</Link>
              <Link href="/paper" className="toplink">Paper</Link>
              <Link href="/content" className="toplink">Content</Link>
              <a href="/api/health" className="toplink">Health</a>
            </div>
          </div>
        </div>
        {children}
      </body>
    </html>
  );
}
