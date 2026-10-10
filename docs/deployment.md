# Deployment handoff — scope v1

Public deployment remains with the deployment teammate. These instructions describe the prepared artifacts; a live deployment must not be claimed before it is exercised.

## Combined application (recommended handoff)

The root Dockerfile builds Next.js and FastAPI in one image. Next.js serves the UI and proxies `/api/v1/*` and `/health` to the internal API. The pretrained model is fetched during image build, pinned by revision and checked with a manifest; it is loaded from local disk at startup. The `scripts/serve.py` supervisor exits if either application process fails.

1. Create a dedicated Railway project and add PostgreSQL.
2. Add this repository as a service using the repository root Dockerfile and `railway.json`.
3. Set `DATABASE_URL` from the project's PostgreSQL reference, `JWT_SECRET` to 32+ random characters, and `DEMO_PASSWORD` to a deliberate 12+ character presentation password. No secrets belong in the repository.
4. Set `CORS_ORIGINS` to the resulting frontend HTTPS origin. The combined app uses a same-origin proxy, so browser CORS is not necessary for normal use; explicit allowed origins remain available for split hosting.
5. Keep `APP_TIMEZONE=Asia/Karachi`, `SEED_ON_START=true`, and the documented freshness/hold/cutoff policy. Generate an HTTPS service domain for the service's supplied `PORT`.
6. Check `/health`, sign in, update an owned quota, complete a reviewed referral, optimize/approve/activate a plan and reprocess a request. Restart and confirm PostgreSQL retains those events.

Migrations run before startup. Initial seed is idempotent and does not reset a populated pilot. Never put SQLite on an ephemeral hosting filesystem for persistent use. Reset is a deliberate CLI maintenance operation, not a public API route.

## Separate Vercel frontend / Railway backend

The backend-only Dockerfile and `backend/railway.toml` remain available. Set the Railway repository root to `backend`. Configure the same database/auth/model-policy environment values.

For Vercel, use root `frontend`, Node 22+, `npm ci`, and `npm run build`. Set `NEXT_PUBLIC_API_BASE_URL` to the public FastAPI HTTPS origin **before building**. Configure that Vercel origin in backend `CORS_ORIGINS`. The direct public API setting overrides the local same-origin proxy.

## Local container rehearsal

Copy `.env.example` to a local root `.env`, populate its three required values, then run `docker compose up --build`. PostgreSQL has a named volume; the app is exposed only on local port 3000. Do not commit `.env` or upload SQLite files.

The CI cold-start test runs the combined container with `--network none`, then checks the UI and API over container loopback. This proves startup does not depend on external model downloads, data scraping or map tiles. The browser's default coordinate map also has no external map dependency.

## Local production frontend

With a prepared API on 127.0.0.1:8000, run `npm ci`, `npm run build`, then `npm start` from `frontend/`. `npm start` copies `.next/static` (and `public` if present) into `.next/standalone`, then starts the generated server. No `next start` command is used. The root Dockerfile already copies those assets into its standalone layout and invokes `server.js` directly.

Use `PORT` and `HOSTNAME` for the frontend listener. `API_PROXY_TARGET` is a private build-time override for the proxy destination; the acceptance harness uses port 18000 to isolate its database. Rebuild without that override for the standard container/internal API on 8000. For a split public frontend use `NEXT_PUBLIC_API_BASE_URL` as described above.

Follow [browser acceptance](browser-acceptance.md) for the reproducible local production/demo check. A successful local test does not establish a public HTTPS deployment. Public handoff still requires a hosting project, configured secrets/PostgreSQL, migration, deliberate seed, and a recorded live restart/persistence check.

## Boundaries

Use only synthetic request identities, costs and agreements. Seeded accounts share the configured demo password intentionally; this is a presentation setup, not production partner credential provisioning. Real clinical use, user invitations, password recovery and partner governance need a separate controlled-pilot scope. Public hospital pins never establish participation.
