# T00 backend report

**Branch:** `feat/backend-t00-t03`
**Status:** Review handoff; no target feature behavior is claimed as implemented.

## Changes

- Added `docs/api-contracts.md` with the agreed `/api/v1` target, `/api`
  compatibility boundary, target DTOs, state vocabularies, route/task/fixture
  index, role and facility checks, expected-version conflicts, idempotency
  replay rules, stable errors, Python import interfaces, and integration order.
- Added `docs/assumptions.md` recording the scope differences and controller
  rulings. The target zones remain the synthetic `Central`, `East`, `South`,
  `West`, and `North` labels; they do not assert official boundaries. Target
  public IDs are opaque strings while integer database keys can remain in place.
- Added five target JSON fixtures: capacity, matching, eligibility, immutable
  snapshot, and solver. The monthly planning fixture has disjoint cohorts of 8,
  7, and 5 synthetic requests, and PKR 25,000 across subsidy, quota, and mobile
  actions.
- Extracted current behavior into `services/capacity.py`,
  `services/eligibility.py`, `services/referrals.py`,
  `optimization/allocation.py`, and `services/plans.py`. `workflows.py` remains
  a compatibility import surface for `main.py` and callers. Existing behavior,
  guarded writes, and route payloads were kept intact.
- Updated `todo.md` with T00 ownership, agreed branch/lane boundaries, the
  completed shared-contract checklist, and evidence. Updated `.gitignore` so
  the T00 report can be tracked while other local `.superpowers` files remain
  ignored.

## Verification

- Focused legacy workflow regression: `python -m pytest
  tests/test_workflows.py -q` — **18 passed** on SQLite.
- Full backend suite with the disposable PostgreSQL `TEST_DATABASE_URL`:
  `python -m pytest -q` — **36 passed** across SQLite and PostgreSQL.
- Lint: `ruff check app tests` — **passed**.
- Parsed every `data/contracts/*.json` fixture — **5 valid JSON files**.
- `git diff --check` — **clean**.

Pytest reported one existing Starlette/httpx deprecation warning from
`fastapi.testclient`; no dependency changes were made.

## Limits

The contracts are target specifications, not implemented endpoints or
validated operational policy. T00 did not change models, migrations, seed,
auth, freshness enforcement, referral states, budget behavior, snapshots,
target solver behavior, or frontend files. The current `/api` behavior remains
legacy behavior. T02/T03/T04/T05/T07–T12 and T14 own those later changes as
indexed in the contracts. Matching model and threshold selection remains with
T07, and the numeric demo defaults are configuration assumptions rather than
clinical or operational validation. D2/D3 review and integration are pending.
