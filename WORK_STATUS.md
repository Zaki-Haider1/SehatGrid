# AKON MVP work status and handoff

**Date:** 10 October 2026  
**Implementation checkpoint:** `0f3e91a` — Implement scope-v1 primary-care coordination MVP  
**Repository:** https://github.com/Zaki-Haider1/akon  
**Authoritative scope:** [User-supplied MVP README](docs/mvp-scope-v1.md)

## Status at interruption

Implementation is paused at the user's request. The main README-aligned implementation was committed and pushed to `main` at the checkpoint above. Most core features are coded and automated checks have passed, but this is **not a claim that every README requirement or acceptance check is complete**. The remaining items and known simplifications are listed below.

There is **no public deployment URL yet**. Deployment configuration and instructions are in the repository. A local preview was running during development; this is not public hosting.

## Interfaces implemented

There are **two authenticated role interfaces in one application**:

- **Government/planner representative:** participation review, network map, demand intelligence, budget and subsidy management, referral funding approval, monthly optimization, plan approval, results/export and audit.
- **Hospital/provider operator:** assigned-facility profile, service and quota reporting, request intake and matching review, sending/receiving referrals, patient-agreement recording, arrival/completion, offers and resource activation.

A separate patient interface is **not part of the supplied MVP**. Operators record patient agreement and request progress. The earlier three-interface proposal is superseded by the README.

## Implemented features

### 1. Provider network and Islamabad map

- Eight synthetic participating providers and five demonstration catchments, limited to canonical non-emergency primary-care OPD.
- Public hospital coordinates used as attributed geographic context; synthetic participation, quota and demand are explicitly separated from real hospital facts.
- Twelve researched hospital records retained as provenance; eight used in the operational seed.
- Provider registration, planner participation review, service/zone declarations and dated referral quotas.
- Capacity freshness, available/limited/exhausted/unknown states and quota-floor validation.
- MapLibre coordinate map with backend-driven provider status and aggregate unresolved-demand labels.
- Optional OpenStreetMap street layer and a basic SVG fallback when WebGL is unavailable.
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

## Still to implement or reconcile with the README

These items prevent an unconditional statement that every detail of the README is finished:

- [ ] **Planner-configurable referral ranking:** the specified deterministic order and policy version are implemented, but there is no planner interface/API to change the ranking policy.
- [ ] **Manual draft-plan revision with a recorded reason:** plans can be recomputed after inputs change, but direct manual editing/override of draft allocations is not implemented. Any implementation must retain all budget/capacity/eligibility constraints.
- [ ] **Explicit `PROPOSED` referral state:** the current sending action creates an attempt in `AWAITING_CONFIRMATIONS` with its hold. A separately persisted proposed stage from the README state table is not implemented.

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

- [ ] Recheck the final GitHub backend-job conclusion and address any reported failure.
- [ ] Complete a browser rehearsal of operator intake, matching review, recommendations/reservation, receiving acceptance, patient agreement, funding approval, arrival and completion.
- [ ] Complete the browser planning loop: snapshot, compute, approve, resource activation/rejection, reprocess unresolved demand and inspect results/export.
- [ ] Check all new screens at phone and desktop widths, including empty/error states and permission-denied cases.
- [ ] Reconcile the local frontend startup command with Next.js standalone output. `next start` emitted a standalone warning; the combined container uses the standalone server.
- [ ] Re-run relevant checks after implementing the missing README items above.
- [ ] Perform the final five-minute demonstration and record its results against the supplied README acceptance criteria.
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

Resume with the missing README items and incomplete acceptance checks above. No feature implementation was continued while preparing this handoff report.
