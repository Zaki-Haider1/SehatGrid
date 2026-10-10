# AKON MVP work status and handoff

**Date:** 10 October 2026
**Implementation checkpoint:** `0f3e91a` — Implement scope-v1 primary-care coordination MVP
**Repository:** https://github.com/Zaki-Haider1/akon
**Current scope:** [Original supplied MVP README](docs/mvp-scope-v1.md), with the user’s subsequent [three-interface / 3D frontend revision](docs/frontend-redesign.md).

## Dev 3 frontend and local acceptance — 10 October 2026

Dev 3 is implemented on `codex/dev3-acceptance-delivery`, integrating `origin/main` at `a957e00`. The user's new visual direction is implemented as an interactive pale 3D government city with blue/coral hospital blocks, separate reception and onboarding interfaces, persisted service/test catalogs, and monthly plan-versus-delivery/budget outcomes. Ranking, proposal/reservation/cancellation, stale proposal recovery and manual draft revision use the merged API contracts. [Design and role details](docs/frontend-redesign.md), [browser setup](docs/browser-acceptance.md), [sanitized verification evidence](outputs/dev3-verification.json) and [final screenshots](docs/screenshots/) accompany the change.

| Gate | Final local evidence |
|---|---|
| Backend, isolated SQLite | `python -m pytest -q`: **122 passed**, 8 existing warnings, 662.03s. All repository tests and the six onboarding/catalog cases ran with the actual pinned model. |
| Backend lint / migrations | `ruff check .`, fresh `python -m alembic upgrade head`, and `python -m alembic check` passed; no new migration operations. |
| Evaluations | `python scripts/evaluate_allocation.py`: **42 independent exhaustive cases passed**. Matching: 6 development / 14 held-out synthetic examples, retrieval/precision 1.00, false-match 0.00, abstention 0.50, all 14 require manual review. No clinical accuracy claim. Timing-only changes to tracked evaluation reports were discarded. |
| Frontend | `npm run typecheck`, `npm run format:check`, `API_PROXY_TARGET=http://127.0.0.1:18000 npm run build`, and documented standalone `npm start` passed. |
| Browser | **24 distinct cases passed across staged runs**, Chromium **156.0.8078.4**, desktop 1440×1000 and emulated phone 390×844, no automatic retries. Nine desktop operational cases passed in the first full run; the three desktop design/stale cases passed after a close-button fix. Five phone operational cases passed in the first phone run, five remaining cases passed after the controls fix, and the final catalog/stale cases passed after constraining catalog scrolling. The changed desktop catalog case additionally passed again. This is not a single clean 24-case run. |
| Timed operational demo | Desktop **57.121s**, phone **52.375s**, each after isolated synthetic reset. Reviewed intake → proposal → reserve → agreement/acceptance → attendance/completion; actual 8/7/5 allocation, PKR 25,000; approval/activation/reprocessing and real JSON/CSV downloads. Final recorded counts: registered 61, confirmed 43, completed 23, unresolved 18; projected additional 20 versus 2 post-activation confirmed and 2 completed. |
| Restart / offline limits | Browser case restarted the isolated API and verified persisted plan decisions; model assets stayed local (`HF_HUB_OFFLINE=1`). Main demo blocked all non-loopback browser traffic. Production standalone frontend served successfully. Full network-disabled combined-container startup and new PostgreSQL tests are final CI gates; prior merged CI is a baseline only. |
| Visual checks | Iterative screenshots were inspected for government map/details, reception, onboarding/catalog and outcomes at both widths. Final production captures have no development overlays and no document-width overflow. |

Exact staged browser commands, from `frontend/` after the documented isolated setup:

```powershell
node node_modules/@playwright/test/cli.js test --max-failures=1
node node_modules/@playwright/test/cli.js test tests/browser/design.spec.ts tests/browser/stale-proposal.spec.ts --project=desktop --max-failures=1
node node_modules/@playwright/test/cli.js test --project=phone --max-failures=1
node node_modules/@playwright/test/cli.js test --project=phone --grep 'software 3D|manual draft|concurrent|cancel|3D government|onboarder catalog|unseen' --max-failures=1
node node_modules/@playwright/test/cli.js test --project=phone --grep 'onboarder catalog|changed capacity' --max-failures=1
node node_modules/@playwright/test/cli.js test tests/browser/design.spec.ts --project=desktop --grep 'onboarder catalog' --max-failures=1
```

The final full backend validation used a **separate** `sehat-grid-dev3-checks` container with the repository mounted at `/workspace`, working directory `/workspace/backend`, isolated temporary SQLite, and local model path `/app/models/all-MiniLM-L6-v2`. The validation chain was `python -m pytest -q && ruff check . && python -m alembic upgrade head && python -m alembic check && python scripts/evaluate_allocation.py && python scripts/evaluate_matching.py`, after installing the pinned pytest/Ruff/httpx development versions into the prepared acceptance image. The normal running demo and its database were not reset.

Failed attempts were retained as evidence: desktop controls were covered by the detail panel; the detail illustration intercepted Close; phone details covered Rotate; and the catalog table scrolled the document. Each was fixed and its affected checks rerun. One export assertion incorrectly used the plan DTO's `coverage` field instead of the export DTO's `projected`/`additional`. Initial focused backend helper errors were corrected; an incomplete container fixture mount and an interrupted shared-container test run were superseded by the independent 122-test pass. A preview server locked the build directory; stopping that preview allowed the production rebuild. Raw reports/traces remain ignored because they can contain session credentials.

Local V1 acceptance and V2 production-start/reset/demo handoff are verified. Public deployment remains **open**: no hosting project/account access or public URL was supplied. Final branch CI, PR review and merge must be assessed separately. Physical-device Safari acceptance is not claimed.

## Earlier integration verification — 10 October 2026 (historical baseline)

Dev 1's latest fix (`e43c7ee`) is integrated on `integrate/referral-reservation`, branched from `origin/main` at Dev 2's `b840941`, as `c1ab59c`. The original Dev 1 branch remains unchanged. The conflict in `todo.md` was reconciled so the referral and draft-plan revision features are both recorded. [PR #2](https://github.com/Zaki-Haider1/akon/pull/2) passed all six GitHub CI job instances at final PR head `e9259e3`; the push run is [38062705176](https://github.com/Zaki-Haider1/akon/actions/runs/38062705176), and the pull-request run is [38062708947](https://github.com/Zaki-Haider1/akon/actions/runs/38062708947). It was merged on 10 October 2026; merge commit `aa8793a` is on `origin/main`. Read-only code review found no blocking issues.

| Gate | Command / environment | Result |
|---|---|---|
| Backend, SQLite only | From `backend/`, `TEST_DATABASE_URL` unset: `uv run --with-requirements requirements-dev.txt python -m pytest -q` | **116 passed**, 8 existing Alembic/migration warnings, 66.78s. |
| Backend, SQLite + PostgreSQL | Same command with `TEST_DATABASE_URL` and `DATABASE_URL` set to an isolated PostgreSQL 17 database; the project fixtures ran SQLite and PostgreSQL cases | **210 passed**, 13 migration warnings, 148.54s. |
| Ruff | `uv run --with-requirements requirements-dev.txt ruff check .` | Passed. |
| Alembic, SQLite | Fresh temporary SQLite database; `alembic upgrade head`, then `alembic check` | Passed; `No new upgrade operations detected.` |
| Alembic, PostgreSQL | Fresh database on isolated PostgreSQL 17; `alembic upgrade head`, then `alembic check` | Passed; `No new upgrade operations detected.` |
| Matching evaluation | `uv run --with-requirements requirements-dev.txt python scripts/evaluate_matching.py` | Pinned MiniLM; 6 development / 14 held-out synthetic examples; candidate retrieval 1.00, exact-alias retrieval 0.25, suggestion precision 1.00, false-match rate 0.00, abstention 0.50, all 14 held-out examples require manual review. This is not a clinical accuracy claim. |
| Allocation evaluation | `uv run --with-requirements requirements-dev.txt python scripts/evaluate_allocation.py` | **42 independent exhaustive checks passed** for seed `islamabad-primary-care-v1`; tiny synthetic fixtures only. The tracked report was restored because this run changed only nondeterministic timing values. |
| Frontend typecheck | From `frontend/`, after `npm ci`: `npm run typecheck` | Passed (`next typegen` and `tsc --noEmit`). |
| Frontend build | `npm run build` | Passed with Next.js 16.4.0. |
| Frontend formatting | `npm run format:check` | The local Windows run flagged nine unchanged files (`app/globals.css`, `app/layout.tsx`, `app/page.tsx`, `components/dialog.tsx`, `components/pilot-map.tsx`, `lib/api.ts`, `next.config.ts`, `tsconfig.json`, `package.json`). `git ls-files --eol` reports LF in the index and CRLF in the Windows worktree. Both Linux GitHub frontend jobs passed, including `format:check`; no frontend files differ from `origin/main`. |

The backend now proves that `POST /referrals` creates `PROPOSED` without a hold, `POST /referrals/{id}/reserve` performs the hold on the same attempt, stale proposals expire and reopen the request, and Dev 2's draft-plan revision behavior remains covered. No frontend source was changed. The existing UI has not been updated for a Reserve action; browser acceptance remains with Dev 3 and is not complete. PR #2's required CI checks passed, read-only review found no blocking issues, and the merge is confirmed on `origin/main` as `aa8793a`.

## Status at interruption

**10 October 2026 follow-up:** Development has resumed. Dev 1's referral proposal/ranking backend landed at `b3c13de`. Dev 2's draft revision backend is committed at `9e5d9e5` on `codex/dev2-plan-revision`, with [draft PR #1](https://github.com/Zaki-Haider1/akon/pull/1), focused tests and a versioned UI fixture. See [the handoff](docs/dev2-plan-revision.md) and current `todo.md`. The interruption report below is historical. Public deployment is now explicitly required by the user and remains open until a live URL and persistence/restart evidence exist.

### Dev 2 verification — 10 October 2026

Ran from `backend/` in the isolated Dev 2 worktree using Python 3.12, pinned development dependencies and the actual pinned MiniLM model preloaded by `scripts/preload_model.py`. Databases were isolated from the existing demo. Windows' default pytest temporary directory denied access; the successful commands use a worktree-local temporary directory instead.

| Command | Result |
|---|---|
| `python -m pytest -xq --basetemp=.pytest_cache/dev2-final-sqlite` with `TEST_DATABASE_URL` unset | **115 passed**, including 35 revision cases, on the combined Dev 1/Dev 2 code. Eight existing Alembic configuration/legacy constraint reflection warnings; no failures. |
| `python -m pytest -xq --basetemp=.pytest_cache/dev2-final-pg tests/test_plan_revision.py -k 'postgresql and (concurrent or race or preserves_solver or keeps_fixed or multiple_revisions or handoff_fixture)'` with `TEST_DATABASE_URL` pointing to an isolated PostgreSQL 17 container | **6 passed**, 51 deselected. Covers revised approval/export, mobile activation, fixture, concurrent revisions, revision/approval race and legacy/multiple revisions. |
| `ruff check .` | Passed. |
| `alembic upgrade head`, then `alembic check` with isolated PostgreSQL `DATABASE_URL` | Passed; no new upgrade operations detected. |
| `python scripts/evaluate_allocation.py` | **42 independent exhaustive checks passed**. Runtime-only changes to the existing evaluation artifact were discarded. |

Revisions consume no funds/quota before approval; invalid edits roll back, original solver results remain preserved, and revised approval requires the displayed version. No migration or dependency was added. Dev 3 still owns the planner editor, reload/error/mobile browser acceptance and required public deployment. PR review and CI passed; merge remains open. Local backend checks do not establish browser or deployment acceptance.

Implementation is paused at the user's request. The main README-aligned implementation was committed and pushed to `main` at the checkpoint above. Most core features are coded and automated checks have passed, but this is **not a claim that every README requirement or acceptance check is complete**. The remaining items and known simplifications are listed below.

There is **no public deployment URL yet**. Deployment configuration and instructions are in the repository. A local preview was running during development; this is not public hosting.

## Interfaces implemented

The original checkpoint had two interfaces. The current frontend revision has **three authenticated interfaces**:

- **Government representative:** pale 3D hospital city, search and data layers, floating facility details, participation/ranking policy, budgets, optimization/revision/approval, monthly outcomes and exports.
- **Hospital receptionist:** reviewed intake, proposals/reservations, sending/receiving/rerouting, patient agreement, arrival/completion, offers and activation.
- **Hospital onboarder:** profile/service eligibility, dated quota and persisted service/test catalog with prices, daily capacity and availability.

A separate patient interface is **not part of the supplied MVP**. Operators record patient agreement and request progress. The user’s later three-interface request concerns a separate hospital onboarder, not a patient portal, and supersedes the original two-interface layout.

## Implemented features

### 1. Provider network and Islamabad map

- Eight synthetic participating providers and five demonstration catchments, limited to canonical non-emergency primary-care OPD.
- Public hospital coordinates used as attributed geographic context; synthetic participation, quota and demand are explicitly separated from real hospital facts.
- Twelve researched hospital records retained as provenance; eight used in the operational seed.
- Provider registration, planner participation review, service/zone declarations and dated referral quotas.
- Capacity freshness, available/limited/exhausted/unknown states and quota-floor validation.
- Three.js city with hospital blocks, backend-driven status, directory search and capacity/demand/funding layers.
- Procedural context roads/buildings and a rotatable software 3D renderer when WebGL is unavailable; no external tile dependency.
- Mobile-clinic activation creates a separate site; it does not move the hospital's campus coordinates.

### 2. Authentication and permissions

- Seeded planner and facility-scoped operator accounts.
- Signed expiring JWTs, salted PBKDF2 passwords and externally configured secrets/demo password.
- Server-side role and assigned-facility checks for reads and mutations.
- Attributable audit events and idempotency receipts for mutations.
- No patient login or unauthenticated role switch granting access.

### 3. Matching and human review

- Actual pretrained `all-MiniLM-L6-v2` model executed through ONNX Runtime.
- Pinned model revision, local preload/checksum manifest and visible failure if required model assets are missing.
- Exact reviewed aliases, fuzzy similarity, embeddings and facility locality/type evidence.
- Supported, unsupported and ambiguous outcomes; persisted human decisions with original input and candidate evidence.
- Reviewed service assignments feed request intake.
- Facility identity links preserve original IDs and do not silently transfer quotas or requests.
- Separate development and held-out matching examples with a saved evaluation report.

### 4. Referral lifecycle

- Separate requests, referral attempts and reservations.
- Feasibility checks for service scope, participation, zone eligibility, date, fresh capacity and funding.
- Deterministic ranking: same zone, lower subsidy, greater remaining quota, stable provider ID.
- Atomic temporary capacity/funding holds.
- Independent receiving-partner acceptance, patient agreement and funding authorization before confirmation.
- Arrival and completion recorded by the receiving operator.
- Rejection, cancellation, expiry, no-show and explicit service-date cutoff rules.
- Completed/forfeited quota is not incorrectly returned to availability.
- Patient-declined requests excluded until explicitly reprocessed.
- Reprocessing after resource activation and protection against duplicate subsidy charges on funded quota.

### 5. Budget and ledger

- Monthly synthetic budgets and a versioned active subsidy rule.
- Held, committed, settled and released funds with transfers between plan pools and referrals.
- Transactional protection against concurrent overspending and overbooking.
- Fixed quota/mobile costs settle once on activation.
- Cancellation, expiry, rejected activation and plan closure release eligible unused funds/resources.

### 6. Demand intelligence

- Counts unique unresolved requests rather than failed referral attempts.
- Aggregation by zone and reason, including unknown-zone requests.
- Separate projected, confirmed and completed results.
- Immutable planning snapshots containing input versions, assumptions and hashes.
- Exclusion of unsuitable, unreviewed, out-of-scope, declined, stale-only, already accommodated or already planned demand.
- Replanning avoids counting the same projected beneficiaries twice.

### 7. Monthly allocation

- Real OR-Tools CP-SAT allocation across subsidies, purchased partner quota and mobile-clinic offers.
- Date/zone/service eligibility, available funds, package costs, overlapping offers and mobile-unit exclusivity.
- Maximize covered requests, then minimize cost, then stable ordered decisions.
- Zero-funded baseline and incremental projected coverage.
- Approval revalidates snapshot freshness and atomically reserves funds/resources.
- Operators activate or reject assigned resources; activation changes persisted operational capacity.
- Rejected resources update remaining cost and projected benefit.
- Plan closure and lazy expiry release eligible unused reservations.
- Aggregate JSON/CSV export includes assumptions, versions, costs and solver status without request IDs.

### 8. Frontend and delivery files

- Role-specific Next.js screens connected to persisted FastAPI results.
- Reason capture for operational decisions such as rejection/cancellation.
- Responsive layout implemented; full final mobile-browser acceptance is still pending.
- SQLAlchemy persistence and non-destructive Alembic migration.
- Seed/reset scripts, pinned dependencies and external configuration.
- Combined frontend/backend container and backend-only container recipes.
- CI workflow for backend, frontend, evaluations and offline container startup.
- Architecture notes, API contracts, policy assumptions, deployment instructions and a demonstration script.

## Superseded or removed extras

- Earlier broad multi-service/daily-slot planning flow and its legacy unauthenticated endpoints.
- Old hospital-profile/map UI that did not match the narrowed operational MVP.
- Broad department/emergency-directory browsing in the operational interface.
- Patient-portal proposal; the MVP uses two roles.

Historical SQL tables and hospital research provenance were retained rather than destructively deleted. They are not active extra product features.

## Verification completed and pending

| Area | Evidence at interruption |
|---|---|
| Local backend | 24 pytest tests passed; lint and migration-drift checks passed. |
| Lifecycle and permissions | Automated coverage includes required confirmations, receiving scope, cancellation/no-show, expiry, identity review and completion. |
| Concurrency | Automated last-unit reservation, concurrent funding holds and simultaneous plan-approval checks. |
| Allocation | Independent exhaustive comparison across 42 tiny cases; recorded coverage/cost matches. Includes overlap, date, stale-resource and funding cases. |
| Matching | Six development examples and 14 held-out examples. Recorded retrieval 1.0, suggestion precision 1.0, false-match rate 0 and abstention 0.5; this is a small synthetic evaluation, not evidence of clinical accuracy. |
| Local frontend | TypeScript, formatting and production build passed. |
| Browser checks | Planner login, dashboard/map and a real computed allocation draft were exercised. Full operator workflow and final mobile-viewport rehearsal were not completed. |
| GitHub frontend job | Last observed result: passed. |
| GitHub combined-container job | Last observed result: passed, including cold startup with network disabled. |
| GitHub backend job | SQLite/PostgreSQL workflow-test step, migrations, lint and evaluation steps passed; the overall backend job was still running at the last successful observation. Final job conclusion was not verified. |
| Public hosting | Not deployed. |

CI run: https://github.com/Zaki-Haider1/akon/actions/runs/38054258367

A fresh CI status lookup during this handoff failed because `api.github.com` could not be resolved. The table records the last observed results and does not treat an unverified job as successful.

## Backend features present on the integration branch

These implementations have local automated evidence above and passed PR #2 CI; frontend acceptance remains a separate Dev 3 responsibility:

- **Planner-configurable referral ranking:** planner-only `GET/PUT /api/v1/referral-ranking` validates and audits a versioned criteria order, keeps eligibility independent of ranking, and returns the applied policy version. The planner UI control remains unimplemented.
- **Manual draft-plan revision with a recorded reason:** `GET /plans/{id}/revision-options` and `POST /plans/{id}/revise` support draft-only human revisions, preserve solver output, revalidate edits and approval, and record revisions for export/audit. The planner editor/browser acceptance remain with Dev 3.
- **Explicit `PROPOSED` referral state:** `POST /referrals` persists a proposal without a hold; `/referrals/{id}/reserve` revalidates and places the hold. Stale proposals expire and reopen requests. The existing UI has not been updated with a Reserve action; operator browser acceptance remains open for Dev 3.

## Known simplifications and architecture limits

These are implementation choices to review when continuing; they are not evidence of production readiness:

- **Persistence:** canonical entity collections are stored in one versioned JSON aggregate in SQL `pilot_state`, protected by database transactions/row locking. They are not separate normalized SQL tables. A strict table-per-entity interpretation of the README would require a further migration. This design also serializes aggregate writes and is intended for a small pilot.
- **Subsidy policy:** one active versioned month-specific rule is stored. Previous planning snapshots retain their inputs, but multiple simultaneously active month-specific schedules are not maintained as a separate history collection.
- **Reviewed aliases:** seeded reviewed aliases and persisted individual matching reviews exist; there is no general alias-maintenance interface or automatic promotion of accepted phrases into the alias dictionary.
- **API documentation:** concrete routes are documented in Markdown; the dynamic API dispatcher does not generate a separate typed OpenAPI operation for every documented route.
- **Expiry:** expiry is processed on API access rather than by a separate background scheduler.
- **Accounts:** seeded demo accounts use an externally configured presentation password. Production account provisioning and recovery are not implemented as a real-provider onboarding system.
- **Data:** locations provide public geographic context, while catchments, partnerships, capacity, costs, requests and outcomes are synthetic. No live hospital availability or real provider agreement is claimed.

## Remaining verification and deployment work

- [x] Open integration PR #2, inspect its CI, merge, and confirm the merge commit on `origin/main`. Both push and pull-request runs passed the backend, frontend and combined-container jobs. The local Windows `format:check` discrepancy is due to CRLF worktree line endings; the Linux CI formatter step passed.
- [x] Complete a browser rehearsal of operator intake, matching review, proposals/reservation, receiving acceptance, patient agreement, funding approval, arrival and completion. Dev 3 evidence is above.
- [x] Complete the browser planning loop: snapshot, compute, revise/approve, resource activation/rejection, reprocess unresolved demand and inspect results/export.
- [x] Check all three interfaces at phone and desktop widths, including empty/error states and permission-denied cases.
- [x] Reconcile local frontend startup with Next.js standalone output and verify the documented `npm start` script.
- [x] Run the requested local backend suites, Ruff, SQLite/PostgreSQL Alembic upgrade/checks, matching/allocation evaluations, and frontend typecheck/build on the integration branch; results are recorded above. The local Windows formatter discrepancy is due to CRLF worktree line endings; Linux CI passed `format:check`.
- [x] Perform the local five-minute operational demonstration and record results and limits above; the three-interface/catalog walkthrough is an additional case.
- [ ] Provision the chosen hosting environment and PostgreSQL, configure secrets, run migrations and initialize synthetic data according to deployment instructions.
- [ ] Verify the deployed application, authentication, API proxy, persistent data, model availability and restart behavior, then record the public URL.

## Intentionally outside this MVP

A patient self-service portal, forecasting, emergency triage, clinical decision automation, real payment processing, live EHR integration and production hospital onboarding are not hidden unfinished MVP features.

## Where to continue

- [Scope authority](docs/mvp-scope-v1.md)
- [Setup and run instructions](README.md)
- [Architecture and tradeoffs](overview.md)
- [API contracts](docs/api-contracts.md)
- [Operational assumptions](docs/assumptions.md)
- [Role interfaces](docs/role-portals.md)
- [Hospital data provenance](docs/islamabad-directory.md)
- [Demo script](docs/demo-script.md)
- [Deployment handoff](docs/deployment.md)
- [Matching evaluation](outputs/matching-results.json)
- [Allocation evaluation](outputs/allocation-results.json)

PR #2 is merged on `origin/main` as `aa8793a`, after its final head passed all six CI job instances. Dev 3's browser acceptance, Reserve UI and three-interface redesign are locally verified on the delivery branch. Public deployment, final branch CI, review and merge remain open; do not claim full MVP acceptance until those gates are satisfied.
