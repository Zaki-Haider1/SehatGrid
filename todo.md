# SEHAT GRID — current delivery board

Updated 10 October 2026 after [integration PR #2](https://github.com/Zaki-Haider1/akon/pull/2) merged to `origin/main` as `aa8793a` (merge commit), based on `b840941` and integrating Dev 1's `e43c7ee` as `c1ab59c`. All six GitHub CI job instances passed at final PR head `e9259e3`: [push run 38062705176](https://github.com/Zaki-Haider1/akon/actions/runs/38062705176) and [pull-request run 38062708947](https://github.com/Zaki-Haider1/akon/actions/runs/38062708947). Local results and the Windows line-ending note are recorded in [WORK_STATUS.md](WORK_STATUS.md). The earlier CI runs [38054258367](https://github.com/Zaki-Haider1/akon/actions/runs/38054258367) and [38058683201](https://github.com/Zaki-Haider1/akon/actions/runs/38058683201) verify earlier commits only; neither covers this integration. The prior board described pre-MVP code and incorrectly marked most implemented features as missing. This board supersedes it.

The team has three developers. Names are deliberately unassigned; claim a lane or exchange tasks as needed. Each numbered task has one owner and its own acceptance evidence. A task marked **coded** means the repository implements it; **verified** means the cited check ran; **open** means work remains. Do not infer full product acceptance from CI.

## Current state

**Dev 3 update:** Three interfaces and the user's 3D government-city revision are locally implemented and verified on `codex/dev3-acceptance-delivery`, based on `origin/main` at `a957e00`. **24 distinct Chromium desktop/phone cases passed across staged runs**, with 122 backend tests, frontend typecheck/format/build, migrations and evaluations passing. Exact commands, failed-attempt fixes and limits are in [WORK_STATUS.md](WORK_STATUS.md) and [sanitized evidence](outputs/dev3-verification.json). Final implementation CI passed at bb64845; PR #4 review/merge remain pending and public hosting is deferred by the user.

| Area | Status | Evidence and limit |
|---|---|---|
| Narrow pilot, provider network, three authenticated interfaces, permissions and audit | Coded; locally verified on Dev 3 branch | Eight synthetic providers, five Islamabad catchments, one routed non-emergency primary-care service; separate government/reception/onboarding roles and catalog guards. |
| Matching and human review | Coded; small evaluation | Pinned MiniLM/ONNX inference and persisted review in `matching.py`; `outputs/matching-results.json` covers 6 development and 14 held-out synthetic examples. No clinical accuracy claim. |
| Referral lifecycle, capacity, funding and ledger | Backend merged; UI/browser locally verified | Proposal-first creation, reserve holds, HTTP-200 expired-proposal recovery, cancellation, receiving agreement/attendance/completion, permission and stale guards exercised at both browser widths. |
| Unique unresolved demand, snapshots and monthly three-action allocation | Backend merged; planner UI/browser locally verified | Worked 8/7/5, PKR 25,000 loop, manual revision/reason/original solver export, activation/rejection/reprocessing, monthly delivery and 42 independent allocation cases. |
| Islamabad 3D city, three interfaces and JSON/CSV export | Coded; locally verified | Real WebGL geometry and software 3D fallback, searchable hospital blocks/data layers, reception desk, persisted onboarding prices/capacities, outcomes and exports; 24 distinct desktop/phone cases. |
| CI and local delivery package | PR #2 CI passed; deployment open | Both push and pull-request workflows for PR #2 passed backend, frontend and combined-container jobs. CI includes PostgreSQL, migrations, evaluations and an offline container cold start. No public URL or live restart check. |

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

**Owner:** Dev 1 backend / Dev 3 frontend. **Status:** Backend merged in PR #2; planner ranking UI, operator ordering/version changes and stale/permission recovery locally verified on the Dev 3 branch. Implementation CI passed; PR #4 review/merge remain pending.

- [x] Define allowed ordering controls in `docs/api-contracts.md` without allowing a policy to bypass service, suitability, zone, date, freshness, capacity or funding eligibility.
- [x] Persist a versioned planner policy; expose planner-only read/update API and include the applied version in recommendations. Keep deterministic stable-ID tie breaking.
- [x] Test default behavior, changed ranking, unauthorized update, stale policy version, eligibility filtering and reservation recheck.
- [x] Add the planner control through Dev 3's UI lane using the versioned contract example in `docs/api-contracts.md`; browser checks pass at both widths.

**Backend baseline evidence:** PR #2 passed 116 SQLite-only tests and 210 PostgreSQL-enabled cases, Ruff and evaluations, and merged with CI green. Dev 3 additionally passed the current 122-test SQLite suite and ranking browser cases at both widths; implementation CI passed; PR #4 review/merge remain pending and public deployment is deferred.

**Done when:** A planner can change ranking, operators see the new order and version, and ineligible providers never appear. Record test command and PR.


### R2 — Explicit referral `PROPOSED` stage

**Owner:** Dev 1 backend / Dev 3 frontend. **Status:** Backend merged in PR #2; reception proposal/reserve/cancel/reload and expired-proposal recovery locally verified on the Dev 3 branch. Implementation CI passed; PR #4 review/merge remain pending.

- [x] Make normal `POST /referrals` persist a `PROPOSED` attempt; reserve that same attempt into `AWAITING_CONFIRMATIONS` only after current eligibility/version checks. `/referrals/proposals` remains a proposal-only alias.
- [x] Keep one active attempt per request, preserve history and idempotency, and ensure proposals have no quota or ledger effect. Stale proposals expire on state/recommendation reads or reserve; sender cancellation remains available and reopens the request.
- [x] Update route contract, scope route catalogue, focused lifecycle/concurrency tests, and exact request/response examples for Dev 3.
- [x] Update reception UI through Dev 3 and complete local lifecycle/browser acceptance at both widths.

**Dev 3 handoff:** Use `POST /api/v1/referrals` with the selected `request_id`, `capacity_id`, `capacity_version`, and `facility_version`; render its `status: "PROPOSED"` response. On the sender's Reserve action, call `POST /api/v1/referrals/{id}/reserve` with `{}` and a new idempotency key; it returns the same ID as `AWAITING_CONFIRMATIONS` with `expires_at`, or `EXPIRED` with a refresh message if inputs changed. Show Cancel for `PROPOSED` and call `POST /api/v1/referrals/{id}/cancel` with a reason. See the exact JSON in [API contract examples](docs/api-contracts.md#proposed-referral-attempt). No frontend files were changed in this backend handoff.

**Done when:** A proposal survives reload, can be reserved into the existing confirmation flow or cancelled, and never changes ledger/quota before reservation. Backend is merged and reception browser proof is locally recorded at both widths.

**Backend baseline evidence:** PR #2 passed 116 SQLite-only tests and 210 PostgreSQL-enabled cases, migrations on both databases, Ruff and evaluations, and merged as `aa8793a`. Reservation concurrency verifies a single hold. Current Dev 3 local browser acceptance is recorded above; no public deployment is claimed.

### P1 — Manual draft-plan revision with reason

**Owner:** Dev 2 backend / Dev 3 frontend. **Status:** Backend merged in PR #2; draft revision/reason validation, reload/concurrent-edit recovery, displayed-version approval and original solver exports locally verified at both browser widths. Implementation CI passed; PR #4 review/merge remain pending.

- [x] Define a draft-only planner revision operation that records actor, timestamp, reason, prior and revised choices. Preserve original solver output and distinguish a human revision in exports/audit.
- [x] Recheck revised assignments and actions with the same budget, date, service, zone, capacity, offer and mobile exclusivity constraints as optimization. Reject stale snapshot/input versions and unfeasible edits. Approval must revalidate again.
- [x] Add focused valid/invalid/stale/concurrent tests. Give Dev 3 a fixture for the planner edit/reason UI.

**Done when:** A planner can revise a draft for a stated reason; an invalid or stale revision has no side effects; displayed/approved totals and export match the revised persisted plan.

**Handoff:** [Revision API and UI contract](docs/dev2-plan-revision.md), [versioned fixture](data/contracts/plan-revision-v1.json). Approval requires the displayed plan version after a human revision. No migration or new dependency is needed.

**Backend baseline evidence:** PR #2 passed **116 SQLite-only tests** and **210 PostgreSQL-enabled cases**, migrations on both databases, Ruff and **42 independent allocation cases**. Dev 3's current local revision browser checks and 122-test SQLite suite pass; implementation CI passed; PR #4 review/merge remain pending and public deployment is deferred.

### V1 — Browser and responsive acceptance

**Owner:** Dev 3 (Codex). **Status:** LOCAL AND CI ACCEPTANCE VERIFIED on delivery branch; PR #4 review/merge pending. Implementation head `bb64845` passed 24 browser cases in each full CI run and 224 SQLite/PostgreSQL backend cases; [PR CI evidence](https://github.com/Zaki-Haider1/akon/actions/runs/38068866580).

- [x] Automate a reproducible real-browser reception journey: login, matching review, intake, recommendation, proposal/reserve, partner response, patient agreement, funding approval, arrival and completion.
- [x] Exercise planner snapshot → optimize/revise → approve → operator quota/mobile activation or rejection → formerly unresolved reprocessing → results and JSON/CSV export. Verify projected, confirmed and completed counts separately.
- [x] Check phone and desktop widths, empty/error/permission-denied states and stale-version recovery. Add R1/R2/P1 controls against the integrated contracts.
- [x] Fix concrete UI defects; record Chromium 156.0.8078.4, isolated resets, staged commands and inspected screenshots. Government 3D and onboarding catalog persistence/role isolation have separate browser cases.

**Done when:** The operational demo completes in a browser after a fresh seed and survives refresh, all three interfaces are usable at phone/desktop widths, and numbers match persisted state. Local checks satisfy this; physical-device Safari is not claimed.

### V2 — Final local delivery and required public deployment

**Owner:** Dev 3 (Codex), with Dev 1 backend support. **Status:** LOCAL HANDOFF VERIFIED in [draft PR #4](https://github.com/Zaki-Haider1/akon/pull/4); PUBLIC DEPLOYMENT PENDING at the user's explicit October 10 request. Resume hosting only when requested and account/project access is available.

- [x] Reconcile production start instructions with standalone output; verify documented `npm start` against the real isolated API and update README/deployment docs. Combined container cold start is additionally in final CI.
- [x] Rehearse the operational demo after isolated reset; verify API restart persistence with local model assets and production frontend start. Desktop 57.121s / phone 52.375s; exact evidence and offline/cold-start limits are in WORK_STATUS.md.
- [ ] Complete the required public deployment: configure secrets/PostgreSQL, apply migration and seed deliberately, then verify HTTPS, authentication, proxy, model, export and persistence across restart. Record URL and smoke evidence. No public deployment is currently claimed.

**Done when:** Local handoff works from documented commands, and a public HTTPS URL with live restart evidence exists. Public deployment is required by the user for the hackathon.

## Integration and completion gates

- [x] Merge R1, R2 and P1 backend contracts through reviewed PR #2 as `aa8793a`, with all six CI job instances passed. Dev 3 UI integration is locally verified; its review/merge is a separate gate below.
- [x] Run backend `pytest -q`, `ruff check .`, SQLite/PostgreSQL Alembic upgrade/checks, matching/allocation evaluations, and frontend typecheck/format/build on the integration branch. PR #2 CI passed for the same tree; exact local results are in `WORK_STATUS.md`.
- [x] V1 local browser and phone acceptance; V2 local reset/production-start/restart/five-minute demo completed with documented limits.
- [x] Final Dev 3 implementation CI at `bb64845`: both workflows green, including expanded PostgreSQL suite, full 24-case browser run and combined app offline cold start. Later handoff changes are documentation/evidence only.
- [ ] Review and merge [Dev 3 draft PR #4](https://github.com/Zaki-Haider1/akon/pull/4).
- [x] Update `WORK_STATUS.md` with merged commits, exact commands/results and remaining limits.
- [ ] Record the required public URL and live persistence/restart evidence after deployment.

The earlier CI successes are baselines for earlier commits only; PR #2 checks cover this integration. Keep reports of failed checks and partial outcomes with their fixes. Claim MVP completion only after the open scope gaps and acceptance gates above pass.
