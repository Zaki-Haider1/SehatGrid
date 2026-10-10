# Hosting handoff

Target: Vercel for the frontend, Railway for FastAPI and PostgreSQL. These instructions follow the official [Next.js/Vercel guide](https://vercel.com/docs/frameworks/full-stack/nextjs) and [FastAPI/Railway guide](https://docs.railway.com/guides/fastapi).

## Railway

1. Create a project and add PostgreSQL. Keep its actual credentials in Railway variables.
2. Add a service from this GitHub repository. Set its **root directory to `/backend`**. Use the included Dockerfile and set the config file path to `/backend/railway.toml` if Railway does not detect it automatically.
3. Set `DATABASE_URL` to the PostgreSQL service's connection URL using Railway's variable reference picker. Both `postgres://` and `postgresql://` are normalized to the psycopg SQLAlchemy driver.
4. Set `APP_TIMEZONE=Asia/Karachi`, `SEED_ON_START=true`, `ENABLE_DEMO_RESET=false`, and initially `CORS_ORIGINS` to the expected frontend domain. Keep one API replica for the MVP.
5. Deploy and generate a public HTTPS domain. `/health` must return `{"status":"ok"}`; `/docs` must load. The container runs Alembic before serving and seeds only if the database is empty.

Do not host the SQLite demo file on an ephemeral container filesystem. PostgreSQL must be attached for persistence. Railway supplies `PORT`; the container binds to `0.0.0.0` and uses it.

## Vercel

1. Import the repository, select Next.js, and set **root directory to `frontend`**.
2. Use Node.js 22+, install `npm ci`, and build `npm run build`.
3. Set `NEXT_PUBLIC_API_URL=https://YOUR-API-DOMAIN` before building; no trailing path is needed.
4. Deploy. Set the API's `CORS_ORIGINS` to the exact frontend HTTPS origin, then redeploy/restart the API. Comma-separate additional approved preview origins explicitly; `*` is not used.
5. If the API URL changes, rebuild/redeploy the frontend because `NEXT_PUBLIC_` variables are baked into the browser bundle.

## Verify the public deployment

- Dashboard loads the seeded providers and dated capacity without CORS or mixed-content errors.
- Update capacity, create a request, choose a provider, confirm, and complete.
- Generate and approve an allocation plan; inspect budget deduction and reprocessed referrals.
- Refresh the page and restart the API service: data remains in PostgreSQL.
- Check GitHub CI. The workflow runs migrations and backend tests against PostgreSQL and SQLite and builds the frontend.
- Keep demo reset disabled unless hosting an explicitly disposable demo. There is no authentication in this MVP, so every visitor has operator/planner access. Keep only synthetic data.

Hosting account access, project selection, and service/domain creation are external setup steps. No public deployment should be claimed until the URL and full workflow have actually been verified.
