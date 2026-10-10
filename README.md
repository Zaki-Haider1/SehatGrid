# Sehat Grid

A healthcare coordination MVP for Islamabad: a sourced real hospital directory and geographic map, with simulated capacity, care requests and funding. Providers share dated demo capacity, operators refer care requests, and planners fund additional demo service slots.

## What works

- Interactive MapLibre street map with 12 researched Islamabad hospitals, geographic pins, zoom/pan and public/private markers.
- Searchable hospital directory with addresses, sectors, business contacts, published services/hours where verified, coordinate evidence and per-hospital source links.
- Provider registration, duplicate-name review, service directory and daily demo capacity updates.
- Request intake → provider recommendations → atomic slot reservation → partner confirmation → completion. Cancellation releases a reservation and reopens the request.
- Unresolved demand grouped by zone, service, and current capacity gap.
- Actual OR-Tools integer optimization, budget-constrained plan review, atomic approval, capacity activation, and automatic retry of unresolved requests.
- Human-reviewed service suggestions using RapidFuzz, JSON export, optional demo reset, and synthetic seed data.
- Operator/planner view switching without authentication, as requested.

**Database choice for judges:** PostgreSQL transactions let us reserve capacity and commit funding atomically, preventing concurrent requests from overbooking or overspending. Check constraints and conditional updates enforce these invariants in the database.

Read [overview.md](overview.md) for architecture, schema, API contracts, decisions, and limitations. Read [docs/deployment.md](docs/deployment.md) for the hosting handoff and [docs/demo.md](docs/demo.md) for the demo walkthrough.

Read [docs/islamabad-directory.md](docs/islamabad-directory.md) for the research, coordinates and accuracy limits, and [docs/role-portals.md](docs/role-portals.md) for the planned government, hospital and patient interfaces. Directory facts do not establish affiliation, eligibility, prices or live capacity at these hospitals.

## Local development

Requirements: Python 3.12, Node.js 22+, and npm. Docker is optional. Dependencies are pinned in `backend/requirements*.txt` and `frontend/package-lock.json`.

From the repository root, Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. Interactive API docs are at `http://localhost:8000/docs`. Startup seeds demo workflows once and syncs the curated hospital directory on subsequent starts, preserving capacity, referrals and funding. The initial dataset includes seven days of simulated capacity and six unresolved demo requests dated on first startup. If the date changes, select the original demo date or reset a disposable demo database explicitly.

On macOS/Linux, use `python3.12 -m venv .venv`, `.venv/bin/python`, and `cp` in place of the Windows commands.

### PostgreSQL locally

```powershell
docker compose up --build -d
cd frontend
npm ci
npm run dev
```

Compose runs PostgreSQL and the API; the frontend runs separately. The database volume persists. Compose credentials are for local synthetic development only. Do not use them for hosting.

### Seed and reset

`SEED_ON_START=true` seeds demo workflows only in an empty database and syncs directory facts in existing databases. The six original synthetic hospitals are upgraded in place, preserving their IDs and demo history. To run the seed/directory sync explicitly after migrations:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.seed_cli
```

For a disposable demo only, set `ENABLE_DEMO_RESET=true` and restart the API. The dashboard then exposes a confirmed reset action. It deletes all demo changes and reseeds. Leave this disabled on shared deployments.

## Verification

```powershell
cd backend
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m alembic check
cd ../frontend
npm run typecheck
npm run build
```

The tests include concurrent attempts to reserve one slot, concurrent attempts to reserve the same request, concurrent plan approvals, budget changes, rollback, cancellation, date isolation, and referral transitions. Set `TEST_DATABASE_URL` to a dedicated PostgreSQL test database to run the same tests against PostgreSQL as well. Tests create and remove uniquely named test schemas; the CI workflow supplies a disposable database.

## Deployment status

The repository includes the backend Dockerfile, migrations, Railway config, environment examples, and GitHub CI. Hosting needs a Vercel project and a Railway project with PostgreSQL connected to this repository. A public URL is only available after that hosting step succeeds; the local preview is not a public deployment.
