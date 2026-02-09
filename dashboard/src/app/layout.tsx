import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Polymarket Bot Dashboard',
  description: 'Open-crawpro dashboard',
};

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
            <div className="badge">
              <span className="dot" />
              Light UI / ChatGPT-like accent
            </div>
          </div>
        </div>
        {children}
      </body>
    </html>
  );
}
