# SEHAT GRID — current delivery board

Reviewed 10 October 2026 against [scope v1](docs/mvp-scope-v1.md), the implementation at `49c44b4`, referral ranking backend commit `69f2110`, [WORK_STATUS.md](WORK_STATUS.md), tests, evaluation artifacts and CI run [38054258367](https://github.com/Zaki-Haider1/akon/actions/runs/38054258367). Follow-up review checked CI run [38058683201](https://github.com/Zaki-Haider1/akon/actions/runs/38058683201), which concluded successfully for `b3c13de`; the route and stale-proposal fixes on this branch were made after that run. The prior board described pre-MVP code and incorrectly marked most implemented features as missing. This board supersedes it.

The team has three developers. Names are deliberately unassigned; claim a lane or exchange tasks as needed. Each numbered task has one owner and its own acceptance evidence. A task marked **coded** means the repository implements it; **verified** means the cited check ran; **open** means work remains. Do not infer full product acceptance from CI.

## Current state

| Area | Status | Evidence and limit |
|---|---|---|
| Narrow pilot, provider network, two authenticated roles, permissions and audit | Coded; automated checks | Eight synthetic providers, five Islamabad catchments, one non-emergency primary-care service; `backend/app/mvp/seed.py`, `auth.py`, `api.py`, `frontend/app/page.tsx`. |
| Matching and human review | Coded; small evaluation | Pinned MiniLM/ONNX inference and persisted review in `matching.py`; `outputs/matching-results.json` covers 6 development and 14 held-out synthetic examples. No clinical accuracy claim. |
| Referral lifecycle, capacity, funding and ledger | Coded; automated checks | `referrals.py`, `common.py`, `api.py`; `backend/tests/test_mvp.py` covers proposal-first creation, reserve, stale recovery, cancellation, permissions, idempotency and concurrent capacity/funding guards. |
| Unique unresolved demand, snapshots and monthly three-action allocation | Coded; backend revision integrated, verification in progress | `intelligence.py`, `planning.py`; worked 8/7/5, PKR 25,000 loop and 42 tiny independent allocation cases. Draft revision backend and fixture are integrated; planner UI remains with Dev 3. |
| Islamabad map, role screens and JSON/CSV export | Coded; partial browser checks | `frontend/components/pilot-map.tsx`, `frontend/app/page.tsx`; planner login/map/allocation draft exercised. Full operator, activation and mobile journeys remain unverified in a browser. |
| CI and local delivery package | Verified CI, deployment open | GitHub run 38054258367 completed successfully for backend, frontend and combined-container jobs. CI includes PostgreSQL, migrations, evaluations and an offline container cold start. No public URL or live restart check. |

The implementation stores versioned canonical collections in a transactional `pilot_state` JSON aggregate, not normalized tables for every entity. This is a documented small-pilot design limit, not an unimplemented feature to silently add. Expiry runs on API access. Seeded partners and operational data are synthetic; public coordinates are geographic context only. A patient portal, emergency triage, forecasting, real payments and real-provider onboarding are outside scope.

## Parallel assignment

Use separate branches/worktrees from current `main`. Do not share a working directory. One developer can take any lane; record the actual owner and PR here when claimed. Keep changes to the listed files where possible. When a shared contract must change, put the request/response example in the PR and notify the other two developers before merging. Integrate via reviewed PRs; do not edit `main` directly. The board integrator updates checkboxes after merges.

| Developer | Independent first task | Primary files | Handoff |
|---|---|---|---|
| Dev 1 — referral policy and state | R1 then R2 | `backend/app/mvp/referrals.py`, referral branches of `api.py` and `schemas.py`, focused tests, `docs/api-contracts.md` | Document versioned policy/state DTOs for Dev 3 browser coverage. |
| Dev 2 — planner revision | P1 | `backend/app/mvp/planning.py`, plan branches of `api.py` and `schemas.py`, focused tests, planner-only UI changes if agreed | Publish draft-revision DTO/fixture for Dev 3; avoid editing referral branches. |
| Dev 3 — acceptance and delivery | V1 then V2 | browser test/config files, `frontend/components/pilot-map.tsx` and scoped UI test fixes, demo/deployment docs | File exact failing journeys as issues to Dev 1/2; use existing APIs first. |

Dev 3 owns `frontend/app/page.tsx` and `frontend/lib/api.ts` during parallel work. If Dev 2 needs a planner control, Dev 2 publishes the backend contract and Dev 3 wires the UI in V1; this is the only planned integration seam. Dev 1 owns shared backend dispatcher/schema edits and reviews Dev 2's plan-route additions before merge. Dev 2 can build and test planning logic in `planning.py` immediately using existing state fixtures, then submit the narrow route patch after Dev 1's shared-file patch lands. No task depends on another developer finishing an unrelated feature.

## Remaining tasks

### R1 — Planner-configurable referral ranking

**Owner:** Dev 1. **Status:** Backend policy, stale-version/recheck coverage, and contract examples are complete on `dev1/referral-ranking-proposals`; planner UI remains open for Dev 3.

- [x] Define allowed ordering controls in `docs/api-contracts.md` without allowing a policy to bypass service, suitability, zone, date, freshness, capacity or funding eligibility.
- [x] Persist a versioned planner policy; expose planner-only read/update API and include the applied version in recommendations. Keep deterministic stable-ID tie breaking.
- [x] Test default behavior, changed ranking, unauthorized update, stale policy version, eligibility filtering and reservation recheck.
- [ ] Add the planner control through Dev 3's UI lane using the versioned contract example in `docs/api-contracts.md`.

**Backend evidence:** The common focused R1/R2 command passed all 8 selected tests: `uv run --with-requirements requirements-dev.txt python -m pytest -q tests/test_mvp.py -k "planner_can_configure_referral_ranking or ranking_never_selects_an_ineligible_provider or proposed_referral or post_referrals or stale_proposal_expires_when_recommendations_refresh"`. Ruff passed. Full backend gate evidence is recorded under R2. CI run 38058683201 is the successful pre-follow-up run for `b3c13de`, not evidence for these local changes. Browser and deployment acceptance remain open.

**Done when:** A planner can change ranking, operators see the new order and version, and ineligible providers never appear. Record test command and PR.


### R2 — Explicit referral `PROPOSED` stage

**Owner:** Dev 1. **Status:** Backend implementation, focused lifecycle checks, and request/response examples are complete on `dev1/referral-ranking-proposals`; operator UI and browser acceptance remain open for Dev 3.

- [x] Make normal `POST /referrals` persist a `PROPOSED` attempt; reserve that same attempt into `AWAITING_CONFIRMATIONS` only after current eligibility/version checks. `/referrals/proposals` remains a proposal-only alias.
- [x] Keep one active attempt per request, preserve history and idempotency, and ensure proposals have no quota or ledger effect. Stale proposals expire on state/recommendation reads or reserve; sender cancellation remains available and reopens the request.
- [x] Update route contract, scope route catalogue, focused lifecycle/concurrency tests, and exact request/response examples for Dev 3.
- [ ] Update operator UI through Dev 3 and complete lifecycle/browser acceptance.

**Dev 3 handoff:** Use `POST /api/v1/referrals` with the selected `request_id`, `capacity_id`, `capacity_version`, and `facility_version`; render its `status: "PROPOSED"` response. On the sender's Reserve action, call `POST /api/v1/referrals/{id}/reserve` with `{}` and a new idempotency key; it returns the same ID as `AWAITING_CONFIRMATIONS` with `expires_at`, or `EXPIRED` with a refresh message if inputs changed. Show Cancel for `PROPOSED` and call `POST /api/v1/referrals/{id}/cancel` with a reason. See the exact JSON in [API contract examples](docs/api-contracts.md#proposed-referral-attempt). No frontend files were changed in this backend handoff.

**Done when:** A proposal survives reload, can be reserved into the existing confirmation flow or cancelled, and never changes ledger/quota before reservation. Backend portion is implemented; browser/operator UI proof remains open.

**Backend gate evidence:** On `dev1/referral-ranking-proposals`, the full local backend CI job passed after the proposal-first route change: Ruff, Alembic upgrade/check, 153 SQLite/PostgreSQL tests (13 existing migration warnings), matching evaluation, 42 allocation checks, and backend-only container build/boot against PostgreSQL. The concurrency tests race the reservation step and verify only one capacity or budget hold is created. CI run 38058683201 concluded `success` for `b3c13de` before this follow-up and does not cover the changes below.

### P1 — Manual draft-plan revision with reason

**Owner:** Dev 2 (Codex). **Status:** Backend and contract coded and locally verified in [draft PR #1](https://github.com/Zaki-Haider1/akon/pull/1) on `codex/dev2-plan-revision`, rebased onto Dev 1's `b3c13de`; review/merge remain open. Planner UI/browser acceptance remain with Dev 3. Checkboxes remain open until integration.

- [ ] Define a draft-only planner revision operation that records actor, timestamp, reason, prior and revised choices. Preserve original solver output and distinguish a human revision in exports/audit.
- [ ] Recheck revised assignments and actions with the same budget, date, service, zone, capacity, offer and mobile exclusivity constraints as optimization. Reject stale snapshot/input versions and unfeasible edits. Approval must revalidate again.
- [ ] Add focused valid/invalid/stale/concurrent tests. Give Dev 3 a fixture for the planner edit/reason UI.

**Done when:** A planner can revise a draft for a stated reason; an invalid or stale revision has no side effects; displayed/approved totals and export match the revised persisted plan.

**Handoff:** [Revision API and UI contract](docs/dev2-plan-revision.md), [versioned fixture](data/contracts/plan-revision-v1.json). Approval requires the displayed plan version after a human revision. No migration or new dependency is needed.

**Backend evidence:** Full SQLite backend suite: **115 passed** (includes 35 focused revision cases); selected PostgreSQL revision/export/activation/legacy/concurrency integration cases: **6 passed**. Ruff, PostgreSQL `alembic check` and **42 independent exhaustive allocation cases** passed. Commands and limits are recorded in `WORK_STATUS.md`. The test model was preloaded from the pinned revision; no matcher stub was used. No planner browser or deployment acceptance is claimed.

### V1 — Browser and responsive acceptance

**Owner:** Dev 3 (claim: unassigned). **Status:** OPEN. **Can start now against existing APIs; extend after R1/R2/P1.**

- [ ] Automate or record a reproducible real-browser operator journey: login, matching review, intake, recommendation, send, partner response, patient agreement, funding approval, arrival and completion.
- [ ] Exercise planner snapshot → optimize → approve → operator quota/mobile activation or rejection → formerly unresolved reprocessing → results and JSON/CSV export. Verify projected, confirmed and completed counts separately.
- [ ] Check phone and desktop widths, empty/error/permission-denied states and stale-version recovery. Include R1/R2/P1 controls after their contracts land.
- [ ] Fix concrete UI defects found; record browser/version, seed reset, steps and screenshots or test output. Do not count backend tests as browser acceptance.

**Done when:** The full two-role demo completes in a browser after a fresh seed and survives refresh, with mobile screens usable and numbers matching persisted state.

### V2 — Final local delivery and required public deployment

**Owner:** Dev 3 (claim: unassigned), with Dev 1 backend support. **Status:** OPEN. **Can start local work now; live checks require hosting access.**

- [ ] Reconcile the local production start instructions with Next.js standalone output; test the documented command/container and update `README.md` and `docs/deployment.md` if needed.
- [ ] Rehearse `docs/demo-script.md` in five minutes after synthetic reset and cold restart, with no runtime model downloads; record exact results and limits in `WORK_STATUS.md`.
- [ ] Complete the required public deployment: configure secrets/PostgreSQL, apply migration and seed deliberately, then verify HTTPS, authentication, proxy, model, export and persistence across restart. Record URL and smoke evidence. No public deployment is currently claimed.

**Done when:** Local handoff works from documented commands, and a public HTTPS URL with live restart evidence exists. Public deployment is required by the user for the hackathon.

## Integration and completion gates

- [ ] R1, R2 and P1 merged with focused tests and contract updates; Dev 3's UI follows their final DTOs.
- [ ] Run backend `pytest -q`, `ruff check .`, `alembic check`, matching/allocation evaluations; run frontend `npm run typecheck`, `npm run format:check`, `npm run build`. Use isolated SQLite/PostgreSQL databases and run relevant CI on merged code.
- [ ] V1 full browser and mobile acceptance completed; V2 local reset/cold-start/five-minute demo completed.
- [ ] Update `WORK_STATUS.md` with merged commits, exact commands/results and any remaining limits; include the required public URL and live persistence/restart evidence.

The existing CI success is a baseline for commit `06390db`; it does not verify future changes. Keep reports of failed checks and partial outcomes with their fixes. Claim MVP completion only after the open scope gaps and acceptance gates above pass.
