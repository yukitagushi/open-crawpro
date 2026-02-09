import { Pool } from 'pg';

let pool: Pool | null = null;

export function getPool(): Pool {
  const url = process.env.DATABASE_URL;
  if (!url) {
    throw new Error('DATABASE_URL is not set');
  }
  if (!pool) {
    // Neon uses TLS; rejectUnauthorized false avoids local CA issues.
    pool = new Pool({ connectionString: url, ssl: { rejectUnauthorized: false } });
  }
  return pool;
}

export async function sql<T = any>(text: string, params: any[] = []): Promise<T[]> {
  const p = getPool();
  const res = await p.query(text, params);
  return res.rows as T[];
}

export function hasDatabase(): boolean {
  return Boolean(process.env.DATABASE_URL);
}
