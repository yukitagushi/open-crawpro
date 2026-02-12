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
              <Link href="/" className="toplink">概要</Link>
              <Link href="/orders" className="toplink">注文</Link>
              <Link href="/fills" className="toplink">約定</Link>
              <Link href="/paper" className="toplink">ペーパー</Link>
              <Link href="/pnl" className="toplink">収益</Link>
              <Link href="/content" className="toplink">収集記事</Link>
              <Link href="/signals" className="toplink">シグナル</Link>
              <Link href="/analytics" className="toplink">分析</Link>
              <Link href="/binance/orders" className="toplink">Binance</Link>
              <a href="/api/health" className="toplink">ヘルス</a>
            </div>
          </div>
        </div>
        {children}
      </body>
    </html>
  );
}
