import { NextResponse } from 'next/server';
import { hasDatabase, sql } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  if (!hasDatabase()) {
    return NextResponse.json({ ok: false, error: 'DATABASE_URL is not set' }, { status: 500 });
  }

  const rows = await sql<{ started_at: any; status: string }>(
    `SELECT started_at, status FROM bot_run ORDER BY started_at DESC LIMIT 1`
  );
  const latest = rows?.[0] ?? null;

  return NextResponse.json({ ok: true, latest });
}
