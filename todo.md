# SEHAT GRID — shared delivery board

Reviewed 10 October 2026 against local `plan.md` scope v1.0 and repository commit `19c0efa`.

**Goal:** Finish the agreed Islamabad primary-care MVP: reviewed service matching → eligible referral → recorded outcome → immutable unresolved-demand snapshot → monthly subsidy/quota/mobile plan → approval → operator activation → valid reprocessing.

This file is the shared, Git-visible execution handoff. `plan.md` is a local, ignored source specification and will not arrive with a fresh clone. Required scope, rules, interfaces, and acceptance checks are therefore summarized here. Checkboxes mean reviewed completion with evidence, not merely code written. All remaining tasks start unchecked.

## 1. What exists and what is still missing

This is a source inspection, not a new runtime qualification. No backend tests, frontend build, or deployment were run during this review; `.venv` and `frontend/node_modules` were absent. Existing tests and CI are evidence of verification infrastructure, not evidence that the full new scope passes.

| Area | Existing implementation / evidence | Remaining against the plan |
|---|---|---|
| Foundation | FastAPI, SQLAlchemy, Alembic, pinned backend/ frontend dependencies; Docker/Compose and CI | Shared versioned contracts, expanded schema, configuration, attributable changes |
| A: provider network | Registration, same-zone fuzzy duplicate rejection, dated capacity editing; `backend/app/main.py`, `models.py` | Public/private ownership, participation activation/suspension, supported services independent of quota, declared zone eligibility, provenance, freshness/version controls |
| B: referrals | Atomic slot reservation; reserved → confirmed → completed; cancellation reopens requests; `workflows.py` | Reviewed service/scope/date/funding fields, separate request/attempt states, independent partner/patient/funding confirmations, arrival, rejection, expiry, cutoff/no-show, idempotency, authorization |
| C: intelligence | Live pending counts and local-capacity gaps in `/api/dashboard` | Unique unresolved units through all attempts, reason taxonomy, unknown-zone/freshness views, resolution funnel, immutable month/date snapshots |
| D: allocation | Actual CP-SAT, dated incremental slot purchases, guarded budget approval, automatic retry | Monthly ledger; subsidy, bounded quota packages and mobile actions; snapshots, input revalidation, solver status, baseline/additional benefit, separate activation |
| ML / review | RapidFuzz top-three service suggestions; duplicate-name guard | Pinned pretrained embeddings, explicit abstention, persisted human reviews and original records, reviewed canonical IDs used downstream, held-out evaluation |
| UI / map | One dashboard with five tabs, role view toggle, selectable SVG schematic, JSON export | Authenticated facility scopes, full workflow screens, operational statuses, Islamabad geography, aggregate demand map, traceable JSON/CSV plan export |
| Verification / delivery | 18 backend test functions; CI declares SQLite + PostgreSQL tests, migrations, container smoke and frontend checks; deployment/demo guides | New invariant tests, independent solver checks, matching results, browser workflow, offline/cold-start rehearsal, verified public deployment if needed |

### Scope differences to resolve first

- `README.md` / `overview.md` describe a deliberately smaller milestone: no authentication, fuzzy-only matching, one global budget, instant funded capacity activation. They do not establish completion of `plan.md`.
- Seeds and map currently use **Karachi**, six providers, six services including dialysis/maternal care, and `urgent` priority. Target **selected Islamabad zones**, roughly eight synthetic public/private partners, and **non-emergency general primary-care OPD**. Do not treat priority as clinical triage.
- Current optimization prioritizes urgent demand, then slots, then cost. Target maximizes additional eligible units, then minimizes cost, then uses stable action IDs. Current unrestricted synthetic slot growth must become bounded offered resources.
- Existing repeat mutations return conflicts; this protects some effects but is not the specified idempotent replay contract. Existing stale-budget checks do not validate capacity/offer/snapshot versions.
- Existing approval activates capacity immediately. Target approval reserves resources/funds; partner/mobile capacity becomes usable only after operator activation.
- Preserve useful existing atomic guards and history. Changing these scope choices requires an explicit team decision recorded in T00, rather than silently marking their target requirements done.

## 2. Working rules and ownership

Three ownership lanes follow the source plan. Assign actual names in the table before claiming work.

| Lane | Person | Owns | Default reviewer |
|---|---|---|---|
| D1 — operational backend / integration | Codex (`feat/backend-t00-t03`) | Schema and migrations; auth, providers, capacity, referral persistence, ledger, approval/activation; shared backend wiring | D2 for invariant/contract changes |
| D2 — decision logic / evidence | To be assigned | Matching and review logic, eligibility/ranking, intelligence snapshots, allocation model, offline evaluation | D1 for persistence/transactions |
| D3 — frontend / presentation | To be assigned | Typed API client, authenticated screens, map, results/export UI, browser checks and rehearsal | D1 or D2 for displayed semantics |

**T00 coordination ruling:** The integration branch is `feat/backend-t00-t03`.
Lane names and boundaries are D1 operational backend/integration, D2 decision
logic/evidence, and D3 frontend/presentation. Only D1 is assigned in this task;
D2/D3 remain named lanes with their assignment pending. `/api/v1` is the target
client prefix; `/api` remains the compatibility surface during migration.

1. Claim one task by changing its status and adding your name/branch/PR in its task card. Confirm dependencies before implementing against a contract.
2. Use a separate clone or worktree per person, with a task branch such as `feat/T03-capacity`. Agree the integration branch at T00; do not share one working directory or push unfinished changes to `main`.
3. **Single writers:** D1 edits `backend/app/models.py`, `schemas.py`, `main.py`, `config.py`, `seed.py`, `.env.example`, backend requirements and `backend/migrations/**`. D3 edits `frontend/lib/api.ts`, `app/page.tsx`, `app/globals.css`, frontend dependencies and lockfile. D1 integrates `.github/workflows/ci.yml`; coordinate edits to `README.md`/`overview.md` during T19. Other lanes submit contract needs to the owner instead of racing on these files.
4. At T00, D1 extracts reusable backend logic into `backend/app/services/` and `backend/app/optimization/`; D3 separates screens under `frontend/components/`. Keep this extraction behavior-preserving. New task-specific services, components, and tests have one task owner. No broad rewrites of `workflows.py` from multiple branches.
5. D1 owns the Alembic revision chain. Do not modify the existing initial revision; queue additive revisions and test upgrades on both databases. If independent branches create revisions, D1 orders/merges them before integration and verifies one intended head.
6. Contract-first parallelism: D1 publishes backend DTOs/example responses; D2 publishes pure decision-service inputs/outputs; D3 builds against the same committed fixtures. Mock screens and pure solver tests can proceed before APIs exist, but integration remains blocked until real dependencies pass.
7. Each task PR states requirement, changed paths, consumed/produced interface, tests run and results, migration impact, and unresolved limits. Merge dependencies first. The owning lane records PR/commit and evidence in this board after review.
8. Each person uses a separate disposable database/schema and port pair. Never reset a teammate's database. Model assets and generated reports belong in their agreed locations, not secret files or ignored local plans.
9. Only one designated integrator edits task statuses in `todo.md` during concurrent PR merges; contributors report claims/completion in their PR. Resolve board conflicts by task ID and preserve evidence.

**Status vocabulary:** `READY` = can start now; `WAIT(Txx)` = needs named handoff; `ACTIVE` = named owner working; `REVIEW` = evidence attached; `DONE` = accepted and integrated. A blocker records the missing artifact/decision and responsible person. Do not infer completion from the baseline table.

## 3. Start order and parallel work

| Wave | D1 can work on | D2 can work on | D3 can work on | Gate before next dependent integration |
|---|---|---|---|---|
| 0: align | T00 contracts, ownership, extraction; then T01 schema/seed | T07 labelled data/model preparation; contribute decision DTOs to T00 | T14 client/screen preparation; contribute UI DTO needs to T00 | Contracts/examples published; shared-file owners agreed |
| 1: independent foundations | T02 permissions, T03 network/capacity, T04 ledger in sequence or separate owned PRs | Finish T07; T09 pure eligibility against fixtures; T10 aggregation fixtures | T14, then T15 operational screens against fixtures | T01–T04 migrated backend; decision DTOs stable |
| 2: operational loop / intelligence | T05 referral lifecycle | T08 persisted matching integration; T09 real eligibility; T10 real snapshots | T15 real operator integration; T16 map/intelligence | One scoped reviewed request can reach completion; snapshot agrees with records |
| 3: planning | T06 offer persistence; T12 approval/activation after T11 | T11 optimizer using T06/T10 fixtures; T13 independent evaluation | T17 planner/review UI against T11/T12 fixtures | Approved actions reserve correctly; activated resources enable valid referral |
| 4: qualification | T18 concurrency/migrations/CI | T13 final reports; review T18 quantitative checks | T18 browser journey; T19 export/docs/offline rehearsal | M7 evidence complete; optional T20 hosting smoke |

**Ready today:** D1 claims T00 and designs T01; D2 prepares T07 evaluation/model assets; D3 audits/splits existing UI for T14. D2/D3 must wait for T00 before committing new integration assumptions. Fixture work is parallel preparation, not end-to-end completion.

## 4. Shared contract and scope checklist (T00 output)

Publish `docs/api-contracts.md`, `docs/assumptions.md`, and versioned example JSON in `data/contracts/`. These travel with the repo because the source plan is ignored.

- [x] Declare selected Islamabad zone IDs/origin, `PRIMARY_CARE_OPD`, provider/request IDs, integer PKR, UTC event timestamps, and `Asia/Karachi` dates/calendar months. Unknown-zone records are retained in summaries but excluded from eligible planning until reviewed.
- [x] Declare request states `OPEN`, `IN_PROGRESS`, `UNRESOLVED`, `FULFILLED`, `CANCELLED`, `OUT_OF_SCOPE`; attempt states `PROPOSED`, `AWAITING_CONFIRMATIONS`, `CONFIRMED`, `ARRIVED`, `COMPLETED`, `REJECTED`, `CANCELLED`, `EXPIRED`, `NO_SHOW`. Preserve attempt history independently of request state.
- [x] Declare action states `DRAFT`, `APPROVED`, `PENDING_ACTIVATION`, `ACTIVE`, `CLOSED` plus explicit rejection/cancellation; ledger states `HELD`, `COMMITTED`, `SETTLED`, `RELEASED` with transfer links.
- [x] Define availability as quota minus active holds, confirmed uncompleted, completed, and forfeited units. Publish freshness/hold minutes, local cancellation cutoff, limited-capacity threshold and service-window/no-show rule as configurable demo settings.
- [x] Freeze capacity DTO: facility/service/date, declared quota, held/committed/completed/forfeited/available units, update actor/time, freshness, version, origin. Availability/freshness are server-derived.
- [x] Freeze request DTO: source facility, synthetic reference, zone, original service text, reviewed service/review ID, acceptable dates, staff-recorded in-scope suitability, agreement and funding flags, status/reasons. No real patient details or automatic clinical eligibility.
- [x] Freeze match result/review DTO: candidate IDs/scores/supporting fields, original input, model/revision, `NEEDS_REVIEW`/`NO_SUPPORTED_MATCH`, selected canonical ID, actor/time. Similarity is not probability.
- [x] Freeze offer DTOs: dated units/service/eligible zones, cost, funding-included flag, version/validity, spare-capacity group for quota and mobile-unit/site/date exclusivity for mobile.
- [x] Freeze immutable snapshot DTO: snapshot ID/time/hash, month/date range, unique request IDs/cohorts, exclusions/reasons, capacity/offer/rule versions. Cohorts share service, zone, dates, suitability and funding requirements.
- [x] Freeze solver DTO: snapshot/budget/rule/model versions, selected actions, assignments, baseline/additional units, total/cost breakdown, remaining demand, exclusions, status/objective/runtime/assumptions. `FEASIBLE` never implies `OPTIMAL`.
- [x] Decide versioned `/api/v1` target with a documented `/api` compatibility adapter during client migration. Cover login, facility participation/services/capacity, matching/reviews, requests/recommendations, all referral transitions, intelligence/snapshots, monthly budgets, offers, optimize/review/approve/activate/export and audit.
- [x] Define role/facility checks, expected-version conflicts, idempotency-key replay/body-mismatch behavior, and stable errors: `CAPACITY_CONFLICT`, `BUDGET_EXCEEDED`, `STALE_INPUT`, `INVALID_TRANSITION`, `SERVICE_REVIEW_REQUIRED`, `ROLE_FORBIDDEN`. Include actionable retry/recompute responses.
- [x] Keep a route → task owner → request/response fixture index. A changed interface updates its fixture, Python validation, TypeScript type and consuming tests together.

## 5. Task cards

For each card, fill **Claim: name / branch / PR** and append **Evidence: command + result / artifact / commit** as work proceeds. Files marked “new” are proposed boundaries, not existing code.

### T00 — Agree contracts and remove shared-file collisions

**Owner:** D1, with D2/D3 review. **Status:** REVIEW. **Depends:** none. **Claim:** Codex / `feat/backend-t00-t03` / PR pending.

**Files:** new `docs/api-contracts.md`, `docs/assumptions.md`, `data/contracts/*.json`; backend extraction from `backend/app/workflows.py`, `main.py`. Frontend extraction and client changes are owned by D3 under T14; they do not block this backend handoff.

- [x] Complete section 4, record scope discrepancies and accepted target, agree integration branch and lane names.
- [x] Extract existing functions into task-owned modules without changing existing API behavior; preserve guarded writes and test semantics.
- [x] Publish matching/eligibility/snapshot/solver fixtures, route ownership, import interfaces and migration order so lanes can develop independently.

**Evidence:** `python -m pytest tests/test_workflows.py -q` — 18 passed;
`TEST_DATABASE_URL=<disposable PostgreSQL> python -m pytest -q` — 36 passed
across SQLite/PostgreSQL; `ruff check app tests` — passed; all five contract
JSON fixtures parsed; `git diff --check` — clean. Full notes:
`.superpowers/sdd/backend-t00-t03/T00-report.md`.

**Accept:** All three lanes can identify exact input/output fixtures for their first task; current regression checks still pass after extraction. No new behavior is implemented merely to satisfy this coordination task.

### T01 — Shared entities, migrations and narrow synthetic seed

**Owner:** D1. **Status:** WAIT(T00). **Claim:** Unclaimed.

**Files:** `backend/app/models.py`, `schemas.py`, `seed.py`, `seed_cli.py`, new additive migrations; new `data/seed/` fixtures; `backend/tests/conftest.py`, new `tests/test_migrations.py`, `tests/test_seed.py`.

- [ ] Add users/facility scope, zones, participation/provenance, facility services, dated versioned capacity, reviewed requests/attempts/reservations, match reviews, monthly budgets/ledger, subsidy rules, quota/mobile offers, demand snapshots, versioned plans/actions and audit events. Phase migrations by dependent task rather than landing speculative unused machinery.
- [ ] Keep ownership and funding/capacity counters constrained; preserve canonical IDs and existing history through migration. Document any synthetic-only reseed instead of silently deleting data.
- [ ] Replace Karachi/broad-service fixtures with ~5 Islamabad pilot zones and ~8 explicitly synthetic public/private providers. Include fresh/stale/exhausted data, ambiguous/unsupported text, scope/date/funding exclusions, and all three funded offers.
- [ ] Seed a declared demo clock/version and the disjoint 8/7/5 unresolved cohorts with PKR 25,000; keep any referral walkthrough request separate so the snapshot remains exactly 20 units.

**Produces:** Migrated shared schema and deterministic data consumed by T02–T12. **Accept:** Empty DB and existing-schema upgrade work on SQLite/PostgreSQL; repeat seed does not duplicate; reset deterministically rebuilds counts/origins and declared freshness.

### T02 — Authentication, facility permissions and audit

**Owner:** D1. **Status:** WAIT(T00,T01). **Claim:** Unclaimed.

**Files:** new `backend/app/services/auth.py`, `audit.py`, auth routes; `main.py`, `config.py`, `.env.example`, dependency pins by D1; new `tests/test_auth.py`, `test_audit.py`.

- [ ] Seed operator and planner accounts; implement validated login/session handling with secrets outside Git. Replace unrestricted API mutation access with backend role and assigned-facility checks.
- [ ] Enforce sender/receiver scope, planner-only budget/participation/plan approval, own-resource activation, and any explicit delegated subsidy limit. Planner cannot impersonate partner acceptance.
- [ ] Persist actor/time/object/before-after or reason for mutations and reviewed decisions; expose scoped audit reads.

**Accept:** Unauthenticated access fails; cross-facility edits/responses and undelegated budget actions fail; valid actors succeed and produce audit events. UI role switching never grants backend permissions.

### T03 — Provider/services, capacity freshness and versions

**Owner:** D1. **Status:** WAIT(T01,T02). **Claim:** Unclaimed.

**Files:** new `backend/app/services/providers.py`, `capacity.py`, task-owned routes; schema/config integration by D1; new `tests/test_capacity.py`.

- [ ] Support profile updates, public/private ownership, participation activation/suspension, reviewed supported services and explicit eligible zones independent of daily quota.
- [ ] Add update actor/time/version, computed fresh/unknown/limited/exhausted status, and version-checked quota edits; missing/stale/suspended capacity cannot appear available.
- [ ] Preserve atomic last-unit guards; forbid reductions below held + committed + consumed + forfeited. Refresh restores eligibility; daily unused units do not roll over.

**Produces:** Capacity DTO and transactional hold/commit/consume/release operations for T05/T12. **Accept:** stale/missing refresh, concurrent edit/hold, below-bookings edit, suspension and day isolation tests; API totals match DB counters.

### T04 — Monthly budgets, subsidy rules and transfer ledger

**Owner:** D1. **Status:** WAIT(T01,T02). **Claim:** Unclaimed.

**Files:** new `backend/app/services/budget.py`, budget/subsidy routes; new `tests/test_budget.py`.

- [ ] Replace global `Budget(id=1)` behavior with local calendar-month envelopes/versioned rules and integer PKR holds, commitments, settlements, releases.
- [ ] Implement one transactional budget service for referral and plan funding. Transfer approved subsidy pool funds to referral commitments and then settlement without counting twice.
- [ ] Fixed quota/mobile costs settle once at activation. Funding-included packages need no duplicate subsidy; unassigned pool funds stay committed until explicitly released.

**Accept:** Ledger reconciles; concurrent subsidy/plan commitments cannot exceed monthly authorization; replay/rollback and cancelled/expired release cases preserve balances; month boundaries remain independent.

### T05 — Complete transactional referral lifecycle

**Owner:** D1; eligibility handoff from D2. **Status:** WAIT(T03,T04,T08,T09). **Claim:** Unclaimed.

**Files:** new `backend/app/services/referrals.py`, referral routes; new `tests/test_referrals.py`, retained/adapted `test_workflows.py`.

- [ ] Intake uses source facility, reviewed canonical service and staff-recorded scope/suitability/date/funding fields; reject emergency/out-of-scope use without diagnosis logic.
- [ ] Keep requests and attempts separate; sending approval atomically creates expiring capacity and optional funding holds after rechecking eligibility/version.
- [ ] Record partner accept/reject, patient agree/decline and funding approval independently. Confirm only when all applicable requirements hold; record arrival before completion and settle once.
- [ ] Add expiry, rejection, cancellation cutoff and no-show forfeiture; release unspent funds, retain attempt history and reopen eligible unresolved demand. Completed quota never releases.
- [ ] Implement idempotency for confirmation, cancellation and completion; retries return the original result, and key reuse with another body conflicts.

**Accept:** Full lifecycle, missing confirmation prerequisites, invalid transitions, last-unit races, same-request races, retries, expiry/cutoff/no-show and rollback tests pass. Prior rejected attempts never consume another unit or erase history.

### T06 — Bounded partner quota and mobile offer APIs

**Owner:** D1. **Status:** WAIT(T01,T02,T03,T04). **Claim:** Unclaimed.

**Files:** new `backend/app/services/offers.py`, offer routes; new `tests/test_offers.py`.

- [ ] Persist reviewed dated all-or-nothing quota packages with spare-capacity group, fixed cost, funding-included flag, availability/version and limits.
- [ ] Persist mobile units, predeclared sites/eligible zones/dates, service capacity and fixed costs. Validate synthetic origin and operator ownership.
- [ ] Expose only currently usable offers to snapshot/solver; supply atomic offer claims/releases for T12. Do not infer unlimited spare capacity from exhausted base quota.

**Accept:** invalid/expired/negative offers rejected; overlap groups and simultaneous mobile unit/site/date conflicts represented and testable; offers alone do not increase usable capacity.

### T07 — Pinned semantic matcher and labelled examples

**Owner:** D2. **Status:** READY for preparation; contract integration WAIT(T00). **Claim:** Unclaimed.

**Files:** new `backend/app/services/matching.py`, `data/evaluation/matching_labels.json`, `scripts/evaluate_matching.py`; model/config/dependency requests handed to D1.

- [ ] Choose and record pretrained embedding model/revision, license, local cache path and normalized Unicode/spacing/punctuation pipeline. Preload assets for offline use.
- [ ] Retrieve service/facility candidates using embeddings, reviewed aliases, fuzzy scores and facility locality/type evidence; return IDs/supporting fields and model version.
- [ ] Use development labels to set abstention/ambiguity thresholds; keep separate held-out aliases, similar-but-distinct providers, paraphrases and unsupported descriptions.
- [ ] Missing model is visible; any fuzzy-only fallback is explicitly labelled and cannot qualify the ML milestone.

**Accept:** Local model returns deterministic candidate fixtures; unknown/ambiguous inputs abstain; model identity is recorded. Evaluation evidence is completed under T13.

### T08 — Persist human matching review and canonical links

**Owner:** D2; D1 owns schema/route wiring. **Status:** WAIT(T01,T02,T07). **Claim:** Unclaimed.

**Files:** new `backend/app/services/match_reviews.py`, new `tests/test_matching.py`; review routes and DTOs through D1.

- [ ] Persist original input/source record, candidates/model revision, reviewer correction/accept/decline and actor/time.
- [ ] Require review before assigning request service or accepting facility canonical links. Retain original facility IDs; name similarity never merges requests or quota.
- [ ] Produce a reviewed canonical-service link consumed by intake/eligibility and a duplicate-review history visible to authorized operators/planners.

**Accept:** Unsupported or unreviewed inputs cannot silently become primary care; corrected review changes canonical routing; similar distinct providers remain distinct; cross-scope review fails.

### T09 — Shared eligibility and transparent ranking

**Owner:** D2. **Status:** WAIT(T00); real integration WAIT(T03,T04,T08). **Claim:** Unclaimed.

**Files:** new `backend/app/services/eligibility.py`, new `tests/test_eligibility.py`.

- [ ] Filter participation, reviewed service, recorded suitability, declared zone eligibility, acceptable date, fresh positive capacity, funding requirements and duplicate active reservation.
- [ ] Return feasible candidates plus excluded reasons; rank same-zone first, lower required subsidy next, larger remaining quota next, stable provider ID last. Store policy version.
- [ ] Share this policy between recommendation, reservation recheck, snapshot cohort compatibility and post-activation reprocessing; do not independently approximate it in UI/solver.

**Accept:** Tests cover each exclusion, date-range compatibility, funding-awaiting-authorization, ties and input changes between recommend/reserve; explanations reflect actual checks and promise no wait time.

### T10 — Intelligence, unique demand and immutable snapshots

**Owner:** D2; D1 persists snapshots/routes. **Status:** WAIT(T00); real integration WAIT(T03,T05,T09). **Claim:** Unclaimed.

**Files:** new `backend/app/services/intelligence.py`, `snapshots.py`, new `tests/test_intelligence.py`.

- [ ] Count each unique open eligible request without confirmed accommodation once, including unresolved attempts/holds as defined in contracts; distinguish capacity, affordability, unknown-data and other reasons.
- [ ] Produce partner coverage, fresh exhausted quota, unknown-zone group, freshness and registered/confirmed/arrived/completed funnel. Use declared periods/denominators.
- [ ] Freeze snapshot IDs/cohorts, dates/month, exclusions, inputs/rule versions, timestamp/hash; subsequent live changes never mutate stored inputs.
- [ ] Keep individual identities out of map summaries/shared exports. Record small-cell suppression policy for any future real-data view; synthetic cells remain clearly labelled.

**Accept:** Multiple failed attempts count once; unknown data stays visible; snapshot equals independently queried records and stays immutable; no forecasting/population-demand claim.

### T11 — Monthly three-intervention optimizer

**Owner:** D2. **Status:** WAIT(T00) for fixture work; real integration WAIT(T04,T06,T09,T10). **Claim:** Unclaimed.

**Files:** new `backend/app/optimization/allocation.py`, new `tests/test_allocation.py`; plan persistence/route wiring through D1.

- [ ] Consume immutable snapshot/monthly remaining funds, dated base capacity, quota/mobile offers and subsidy rules. Group only identical eligibility/funding/date requirements and retain request IDs.
- [ ] Model cohort-resource integer assignments and binary package/mobile choices. Enforce request uniqueness, date/service/zone/suitability, fresh base supply, offered spare capacity, overlap/mobile exclusivity and total fixed + required per-unit subsidy costs.
- [ ] Subsidy removes affordability barriers without creating capacity; combined barriers require capacity and funding. Count baseline feasible assignments on the same snapshot before reporting additional accommodation.
- [ ] Maximize additional eligible accommodation, then lower cost, then stable action IDs. Remove current urgent-first objective unless the team explicitly revises scope at T00.
- [ ] Persist actual solver status, objective, runtime, input/model versions, selected actions, assignments, exclusions, cost breakdown and remaining demand. No fabricated fallback result after failure.

**Accept:** PKR 25,000/8+7+5 case gives 20 projected additional units and exact costs; zero-budget/no-supply/stale/mixed barriers and offer conflicts behave correctly; `FEASIBLE`, `OPTIMAL` and failures are distinct. Independent optimality checks belong to T13.

### T12 — Transactional approval, operator activation and reprocessing

**Owner:** D1. **Status:** WAIT(T05,T06,T10,T11). **Claim:** Unclaimed.

**Files:** new `backend/app/services/plans.py`, `activation.py`, plan routes; new `tests/test_activation.py`.

- [ ] Revalidate snapshot/capacity/offer/budget/rule versions at approval; reject changed inputs with `STALE_INPUT` and recomputation guidance. Reserve funds/offers atomically.
- [ ] Persist per-action approval/activation states. Subsidy authorization may activate on approval; partner/mobile capacity remains pending until the owning operator confirms the offered resource.
- [ ] Activate dated capacity/funding exactly once, settle fixed action costs once, release expired/rejected/abandoned holds and account for partial activation without reporting unavailable units.
- [ ] Re-evaluate original unresolved request IDs with shared eligibility; capacity activation never marks requests completed. Store action/resource linkage for later confirmed/completed outcome reporting.
- [ ] Add idempotent approval/activation and concurrent approval/activation guards with consistent lock ordering.

**Accept:** Approval alone does not expose pending partner/mobile quota; stale approval has no side effects; competing plans cannot reserve the same budget/offer/mobile unit; retry cannot double-charge/add quota; activation enables at least one previously unresolved referral with normal confirmations.

### T13 — Independent matching and allocation evidence

**Owner:** D2. **Status:** WAIT(T07,T11). **Claim:** Unclaimed.

**Files:** `scripts/evaluate_matching.py`, new `scripts/evaluate_allocation.py`, `data/evaluation/planning_cases.json`, generated `outputs/matching-results.json`, `outputs/allocation-results.json`, new `tests/test_allocation_oracle.py`.

- [ ] Compare semantic matching with exact/alias baseline on held-out examples; report retrieval success, false-match rate, accepted precision, abstention and manual-review frequency, sample sizes/model revision.
- [ ] Enumerate tiny feasible allocation cases independently of CP-SAT and check coverage/cost/eligibility/date/offer constraints. Compare cost-per-unit greedy under identical constraints; do not assume solver wins every case.
- [ ] Record zero-budget, no-supply, stale data, overlapping quotas, mobile conflicts, funding-included and mixed affordability/capacity cases, time-limited/failure statuses, input hashes and runtime.

**Accept:** Reproducible reports support the exact limited claims used in UI/demo; oracle detects an intentionally invalid allocation; no test/evaluation leakage from threshold tuning.

### T14 — Typed client, screen boundaries and auth integration

**Owner:** D3. **Status:** READY for preparation; contracts WAIT(T00), real login WAIT(T02). **Claim:** Unclaimed.

**Files:** `frontend/lib/api.ts`, `app/page.tsx`, `app/globals.css`; new `frontend/components/screens/` and `frontend/tests/contract-fixtures/`.

- [ ] Read `frontend/AGENTS.md` and installed Next.js guides before frontend implementation. Extract existing tabs/forms to owned screens without changing behavior first.
- [ ] Add contract-matched types/client support for auth, expected versions, idempotency, structured conflicts and request cancellation/timeouts. Use T00 fixtures; no invented backend field names.
- [ ] Render operator/planner and facility scope from authenticated identity. Shared shell displays synthetic label, selected date/month, loading/empty/error/unknown states and refreshes server totals after mutations.

**Accept:** Typecheck/build/format checks; denied/expired-session handling and structured-error fixtures; role toggle cannot bypass backend scope. Screen boundaries allow small task PRs.

### T15 — Operational screens and review workflow

**Owner:** D3. **Status:** WAIT(T14); real integration WAIT(T03,T05,T08,T09). **Claim:** Unclaimed.

**Files:** new `frontend/components/screens/providers.tsx`, `capacity.tsx`, `requests.tsx`, `referrals.tsx`, matching-review components; new browser tests.

- [ ] Facility profile/participation/service editing and own capacity show date, quota counters, update time/freshness/version and recoverable stale conflicts.
- [ ] Intake records minimal synthetic scope/date/funding fields and explicit human service review; never defaults unsupported text into a service. Duplicate review retains sources.
- [ ] Recommendations show exclusion/funding reasons; sender approval, incoming accept/reject, patient agreement, funding approval, arrival/completion, cancellation/expiry/no-show all show persisted states/deadlines.
- [ ] Label numeric similarity as a score, not correctness probability; remove broad-service/clinical-urgency demo assumptions in the old form.

**Accept:** Browser journey completes a scoped request through review and all required confirmations; unauthorized controls, unknown capacity, rejected/expired attempts, conflict recovery and cancellation are covered.

### T16 — Islamabad network and unresolved-demand map

**Owner:** D3. **Status:** WAIT(T14); real data WAIT(T03,T10). **Claim:** Unclaimed.

**Files:** `frontend/components/network-map.tsx`, new `screens/intelligence.tsx`, bundled `data/seed/zones.geojson` or frontend geographic assets; map dependency updates by D3.

- [ ] Replace hardcoded Karachi coordinate projection/copy with agreed Islamabad pilot geography/origin and selectable facility/service/date views.
- [ ] Show active participation, available/limited/exhausted/unknown quota, freshness, coverage, aggregate unresolved reasons and unknown-zone group from backend DTOs.
- [ ] Use MapLibre with licensed/bundled geography, or record an accepted schematic implementation choice in T00. Provide bundled offline fallback/attribution and keep declared eligibility separate from travel accessibility.

**Accept:** Map counts match backend snapshot; stale/missing does not render exhausted or available; no individual request identifiers in tooltips; offline fallback loads without tile/network availability.

### T17 — Monthly planner and staged action review

**Owner:** D3. **Status:** WAIT(T14); real integration WAIT(T04,T06,T11,T12). **Claim:** Unclaimed.

**Files:** new `frontend/components/screens/planner.tsx`, `plan-review.tsx`, offer editors; new browser tests.

- [ ] Select month, inspect held/committed/settled/remaining PKR, maintain permitted quota/mobile offers, select snapshot and run actual optimization.
- [ ] Review subsidy quantities, quota packages/mobile deployments, cost breakdown, baseline and projected additional accommodation, excluded/remaining units and human-readable solver status.
- [ ] Separate approval from operator activation; expose pending/rejected/partial/expired action states, stale-plan recompute and idempotent retry behavior.

**Accept:** UI never claims approval instantly creates usable partner/mobile capacity; totals equal persisted plan/ledger; infeasible/empty/time-limited outputs visible; activated resource leads back to the operational workflow.

### T18 — Integration, concurrency and CI gates

**Owner:** D1 for backend/CI; D2 supplies oracle checks; D3 owns browser tests. **Status:** WAIT(T05,T08,T10,T12,T15,T16,T17). **Claim:** Unclaimed.

**Files:** task-specific `backend/tests/`, retained `test_workflows.py`, `.github/workflows/ci.yml`; new frontend browser test/config files and scripts by D3.

- [ ] Run scoped tests during each task; run full SQLite/PostgreSQL suite, lint, migration upgrade/check and container startup in CI. Verify upgrade of the pre-change schema, not only metadata-created fresh test databases.
- [ ] Cover concurrent last-unit/same-request reservations, budget/offer/mobile claims, idempotency, cutoff/expiry, ledger transfers and rollback; include stale capacity/offer/budget/rule approval conflicts.
- [ ] Add a browser test for review → referral completion → snapshot → mixed monthly plan → approval → activation → formerly unresolved confirmation/completion → export, including projected versus actual totals.
- [ ] Preserve relevant old regression guards; rewrite urgent-objective and instant-approval assertions to match accepted new semantics instead of deleting coverage.

**Accept:** Reproducible commands pass against both DB targets and real frontend/API; artifacts identify input/seed/version and show actual outcomes. Migrations, solver oracle and browser journey are separate gates.

### T19 — Traceable exports, documentation and offline demo

**Owner:** D3 for UI/demo docs; D1 backend export/docs integration; D2 verifies claims. **Status:** WAIT(T13,T18). **Claim:** Unclaimed.

**Files:** new `backend/app/services/exports.py` by D1; new `frontend/components/screens/results.tsx`; `docs/demo.md`, `docs/deployment.md`, new `docs/assumptions.md` updates; `README.md`/`overview.md` by designated integrator; new export tests.

- [ ] Export plan-specific JSON **and CSV** with synthetic scope/origins, input hashes/versions/month, costs/actions/assignments, assumptions/exclusions and solver status. Keep individual identifiers out of shared map/result exports; use internal linkage for audit.
- [ ] Separate projected additional accommodation, post-activation confirmed and completed unique requests; completion rates include period/denominator/pending cohort.
- [ ] Rehearse the five-minute sequence using 8 subsidies + 7 quota + 5 mobile units at PKR 25,000. Reset a disposable DB; cold restart with preloaded model/geography and no external downloads; confirm persistence.
- [ ] Update actual environment names, dependencies, migrations/startup commands and limitations. Do not claim public deployment or measured ML/optimizer benefit without attached evidence.

**Accept:** Export validates against persisted plan/ledger; saved reports and demo counts reconcile; reset/cold-start/offline rehearsal evidence recorded; a fresh clone has sufficient scope/setup context without `plan.md`.

### T20 — Optional public demo deployment

**Owner:** D1 API/PostgreSQL; D3 frontend. **Status:** WAIT(T19, hosting access). **Claim:** Unclaimed.

**Files:** existing `backend/Dockerfile`, `railway.toml`, `docker-compose.yml`, `docs/deployment.md`, frontend environment/build settings as needed.

- [ ] Configure chosen hosts/database, secrets, model assets, origin allowlist and build-time API URL; apply migrations before serving and keep shared reset disabled.
- [ ] Verify actual HTTPS URLs, scoped demo logins, end-to-end workflow, exports and persistence across service restart. Record URLs and smoke evidence.

**Accept:** Public deployment is claimed only after live checks. This is an external handoff, not a hidden condition for local MVP completion; no service creation/submission is authorized by this task board alone.

## 6. Verification commands and evidence recording

Use a dedicated local environment. Current setup requires Python 3.12 and Node 22+. Follow `README.md` setup first; dependency/model/browser-test installation belongs to the respective implementation task. Run from repository root in PowerShell:

```powershell
# Existing baseline commands; require .venv and installed frontend dependencies.
Push-Location backend
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic check
Pop-Location
Push-Location frontend
npm.cmd run typecheck
npm.cmd run format:check
npm.cmd run build
Pop-Location
```

Set `TEST_DATABASE_URL` to **your own disposable PostgreSQL database** before pytest to run the existing fixture on both SQLite and PostgreSQL. Set `DATABASE_URL` separately for migration checks; never run upgrades/reset against a teammate's or real-data DB. T13/T18 must add and document exact evaluation/browser commands when their entrypoints exist; they are not available baseline scripts today.

Completion evidence format: `Txx | owner | branch/PR + merged commit | exact command/result | report/log path | limitations`. Retain failed cases as well as the passing final gate. No current card has runtime completion evidence.

## 7. Milestone gates and source-plan coverage

| Gate | Required accepted tasks | Exit check | Current status |
|---|---|---|---|
| M1 contracts/seed | T00,T01 | Agreed IDs/month/rules/roles and reproducible narrow seed | Partial foundation only |
| M2 operational loop | T02–T05,T08,T09,T15 | Reviewed scoped request → all confirmations → arrival → completion with correct counters | Simplified loop exists; target incomplete |
| M3 ML | T07,T08,T13 matching report | Preloaded embedding inference, persisted review, canonical routing, labelled evaluation | Missing; fuzzy baseline only |
| M4 intelligence | T10,T16 | Unique unresolved snapshot and map agree with DB | Live aggregate baseline only |
| M5 planning | T04,T06,T11,T13 solver report,T17 | Real monthly three-action allocation satisfies independently checked constraints | Daily slot-purchase baseline only |
| M6 closed loop | T12,T15,T17 | Approval → operator activation → valid unresolved reprocessing → separate actual outcomes | Instant synthetic activation baseline only |
| M7 qualification | T18,T19 | Critical tests, ledger reconciliation, exports, reset/offline cold-start and demo pass | Unverified for target scope |

| Source plan sections | Work covering the requirement |
|---|---|
| 1–3 vision, scope and complete loop | T00,T01,T05,T10–T12,T19; M1–M7 |
| 4 users/permissions | T02,T14,T15,T17 |
| 5 provider network | T01,T03,T06,T15,T16 |
| 6 referral coordination | T05,T08,T09,T15,T18 |
| 7 intelligence | T10,T16,T19 |
| 8 monthly allocation | T04,T06,T11–T13,T17 |
| 9 matching and optimization | T07–T09,T11,T13 |
| 10 time, capacity, funding and stale plans | T03–T06,T12,T18 |
| 11 entities/contracts/provenance | T00,T01,T08,T10,T19 |
| 12–16 stack/API/UI/seed/config/setup | T00–T03,T07,T14–T17,T19 |
| 17 verification and metrics | Per-task checks,T13,T18,T19 |
| 18 demo; 19 delivery; 20 definition of done | Waves/ownership above; milestone gates; T18,T19 |
| 21 limits/expansion; 22 pitch | T00,T19; preserve evidence boundaries |

**Completion rule:** M1–M7 must pass with recorded evidence to call the agreed MVP complete. Optional T20 does not substitute for any gate. No forecasting, population-demand estimates, road routing, appointment/wait-time prediction, inpatient queues, diagnosis/triage, real payment/vouchers, capital construction, or scenario-lab expansion is required for this scope.
