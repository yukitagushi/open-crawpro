'use client';

import { useEffect } from 'react';

export function AutoReload({ seconds = 30 }: { seconds?: number }) {
  useEffect(() => {
    const ms = Math.max(5, seconds) * 1000;
    const id = window.setInterval(() => {
      // Hard reload to ensure fresh server-rendered data
      window.location.reload();
    }, ms);
    return () => window.clearInterval(id);
  }, [seconds]);

  return null;
}
