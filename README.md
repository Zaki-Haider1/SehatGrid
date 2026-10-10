# SEHAT GRID

A synthetic, non-emergency primary-care coordination MVP for five Islamabad pilot catchments. The original specification is [docs/mvp-scope-v1.md](docs/mvp-scope-v1.md). The user’s October 10 frontend revision adds three interfaces and a required 3D government map; see [the frontend design and role contract](docs/frontend-redesign.md).

## What runs

- **Hospital receptionist:** reviewed request intake, recommendations and saved proposals, acceptance/rejection, patient agreement, arrival/completion, rerouting/reprocessing, offers and activation.
- **Hospital onboarder:** assigned hospital profile, primary-care eligibility, dated quota, and an editable service/test catalog with PKR prices, daily capacity and availability.
- **Government representative:** interactive 3D city, hospital details and capacity/demand/funding layers; participation and ranking policy; monthly budgets, allocation/revision/approval, funding authorization, monthly outcomes and JSON/CSV exports.
- **No patient portal.** Operators record voluntary patient agreement. No forecasts, diagnosis, emergencies, exact appointment slots, waiting-time predictions, travel-time routing, construction, payment or voucher features.

Next.js/TypeScript and Three.js share a FastAPI backend. A pinned MiniLM embedding model plus RapidFuzz suggests matches; human reviews persist. OR-Tools computes monthly allocations for subsidies, purchased quota packages and mobile visits. All operational data and costs are synthetic. Public hospital coordinates remain separately attributed directory context, not confirmed partnerships.

## Run locally

Use Python 3.12 and Node 22+. From the repository root:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
Copy-Item backend/.env.example backend/.env
# Edit backend/.env: set JWT_SECRET (32+ random characters) and DEMO_PASSWORD (12+ characters).
.venv/Scripts/python.exe backend/scripts/preload_model.py
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe scripts/seed_demo.py
../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, from `frontend/`:

```sh
npm ci
npm run dev
```

Open `http://localhost:3000`. The Next.js server proxies `/api/v1` to FastAPI on port 8000. Use account `planner` or `operator-p01` through `operator-p08` (reception), or `onboarder-p01` through `onboarder-p08` (setup) and the configured `DEMO_PASSWORD`. Existing synthetic demos gain onboarding accounts when the seed command or seed-on-start runs, without resetting requests, plans or funds. New accounts use the configured demo password. Existing accounts are seeded once; changing an environment variable does not silently change persisted account credentials. A deliberate synthetic reset recreates them.

For a separate frontend host, set `NEXT_PUBLIC_API_BASE_URL` at build time and configure backend `CORS_ORIGINS` accordingly. Same-origin local/container operation needs no public API variable.

For a local production frontend, run `npm run build` then `npm start` from `frontend/`. The start script copies static assets into `.next/standalone` and runs its `server.js`. Set `PORT`/`HOSTNAME` to change its listener. The private `API_PROXY_TARGET` build variable changes the default internal API origin (`http://127.0.0.1:8000`); rebuild after changing it. Do not use `next start` with this standalone configuration.

## Reproducible demonstration

```powershell
# From backend/; explicitly discards only the scope-v1 synthetic pilot state.
../.venv/Scripts/python.exe scripts/seed_demo.py --reset
```

Reset seeds eight demo providers, five team-defined pilot catchments, 40 previously accommodated units (20 recorded completed, 20 confirmed), and 20 unresolved units. The service date is explicitly tomorrow in Asia/Karachi, the simulation's dated accounting bucket. Seeded history is a synthetic replay, not an actual chronology of delivered care. Quota freshness is stamped at reset; stale examples are intentionally aged. Do not use these records for real care.

The selected month has PKR 25,000: 8 subsidies Ã— 1,000, a 7-unit quota offer for 7,000, and a 5-unit mobile visit for 10,000. The actual solver returns 20 projected additional accommodations. Approval reserves funds and resources; operators P02 and P08 activate their offered resources; P01 can then refer B/C requests. A mobile activation creates a **separate synthetic site** and preserves the public hospital campus coordinate.

Follow [docs/demo-script.md](docs/demo-script.md). Matching/model files and coordinate-map assets are loaded before presentation. The default map requires no tile network; optional OSM street context uses network access. Missing/corrupt embedding files produce a startup failure instead of fabricated ML results.

## Verification

```powershell
# From backend/
../.venv/Scripts/python.exe -m pytest -q
../.venv/Scripts/ruff.exe check .
../.venv/Scripts/python.exe -m alembic check
../.venv/Scripts/python.exe scripts/evaluate_matching.py
../.venv/Scripts/python.exe scripts/evaluate_allocation.py
```

Set `TEST_DATABASE_URL` to an isolated PostgreSQL connection to run the same workflow suite against PostgreSQL as well as SQLite. Each PostgreSQL test uses its own temporary schema. Frontend: `npm run typecheck`, `npm run format:check`, `npm run build`.

Real-browser acceptance uses Chromium at desktop and phone widths, the production frontend, and a dedicated synthetic API/database. See [browser acceptance](docs/browser-acceptance.md) for exact setup, reset boundaries and evidence. Run `npm run test:browser` after that setup; backend unit tests alone do not count as browser acceptance.

Evaluation artifacts live in `outputs/matching-results.json` and `outputs/allocation-results.json`. Threshold tuning and held-out matching examples are separated. The allocation check independently enumerates 42 tiny cases and records a constrained greedy comparator. These small checks do not establish clinical impact or general model superiority.

## Deployment handoff

The root Dockerfile packages Next.js and FastAPI behind one origin, with the model downloaded at **image build** and loaded locally at runtime. Use PostgreSQL for the hosted instance. The root `railway.json` sets `/health` as the readiness check. Configure `DATABASE_URL`, `JWT_SECRET`, `DEMO_PASSWORD`, and `CORS_ORIGINS`; do not upload local `.env` or SQLite files. `backend/Dockerfile` remains available for a separate backend-only deployment.

The deployer can run `docker compose up --build` after supplying `.env` values at the repository root; this starts PostgreSQL and the complete app on port 3000. The repository does not embed hosting credentials. Production partner onboarding, clinical governance and real operational data are outside this synthetic MVP.

## Documentation

- [Authoritative MVP scope](docs/mvp-scope-v1.md)
- [Architecture and implementation decisions](overview.md)
- [API contracts and error behavior](docs/api-contracts.md)
- [Operational policies and limitations](docs/assumptions.md)
- [Five-minute demo](docs/demo-script.md)
- [Two roles and their permissions](docs/role-portals.md)
- [Verification and scope checklist](todo.md)
- [Islamabad public coordinate sources](docs/islamabad-directory.md)
