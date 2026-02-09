# Dashboard (Next.js + Neon Postgres)

White, simple dashboard with ChatGPT-like green accent.

## Local dev

```bash
cd dashboard
npm install
export DATABASE_URL='postgresql://...'
npm run dev
```

Open: http://localhost:3000

## Vercel deploy

1. Import the GitHub repo in Vercel
2. Set Environment Variables:
   - `DATABASE_URL` (Neon connection string)
3. Deploy

Notes:
- DB access is server-side only.
- If `DATABASE_URL` is missing, the page shows a setup guide.
