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
- Added six target JSON fixtures: capacity, matching, eligibility, immutable
  snapshot, solver, and `routes-v1.json`. The route fixture has exact request/
  response examples for login identity, facility list/register/profile,
  participation, services, capacity, and audit. Later route owners have named
  fixture artifacts and publish-before-consumption gates in the index.
- The monthly planning example has disjoint cohorts of 8, 7, and 5 synthetic
  requests, with PKR 25,000 across subsidy, quota, and mobile actions. Cohort A
  has 8 physically available units but zero usable baseline because its
  PKR 1,000/unit subsidy has no prior authorization. Cohorts B/C have no usable
  base capacity. Snapshot exclusions are carried separately into the solver
  example; its status is illustrative only and runtime is null.
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
- Initial implementation pass parsed all then-existing fixtures — **5 valid JSON files**.
- `git diff --check` — **clean**.

Pytest reported one existing Starlette/httpx deprecation warning from
`fastapi.testclient`; no dependency changes were made.

## Review follow-up verification

After the review fixes, a Python 3.12 JSON cross-consistency check parsed all
six contract fixtures and verified: the snapshot digest against the documented
canonical encoding; 20 unique cohort request IDs and unit counts; zero-baseline
funding facts; exact transfer of snapshot exclusions into the solver result;
solver assignments against action/cohort units; PKR 25,000 total cost/budget;
the example-only/null-runtime markers; and all nine required T01–T03 route
examples with request/response bodies where applicable. Result: **PASS**. The
verified digest is `sha256:89200f5f36a37270b221297cb423cc2d58194c85d2684a55ee342ba34785f437`.
Command: `@' <Python assertions for these checks> '@ | .\\.venv\\Scripts\\python.exe -`
from the repository root. This was a fixture consistency check, not a solver
execution or application test. The legacy test suite and Ruff were not rerun
because these follow-up changes only alter JSON fixtures and docs.

## Second review follow-up

The login actor contract now returns `facility_ids: string[]` for all assigned
facilities, supports multiple operator assignments, and does not require an
active facility selection. A focused JSON identity check parsed all six
fixtures and verified the login actor's role/ID fields, string-list type, and
absence of the singular `facility_id` field. Result: **PASS**. No application
tests or Ruff were rerun; this round changes only the login DTO documentation
and fixture.

## Limits

The contracts are target specifications, not implemented endpoints or
validated operational policy. D2/D3 assignment and contract review remain
pending; no agreement from those lanes is claimed. T00 did not change models,
migrations, seed, auth, freshness enforcement, referral states, budget
behavior, snapshots, target solver behavior, or frontend files. The current
`/api` behavior remains legacy behavior. Later routes and behaviors remain with
their indexed owning tasks. Matching model and threshold selection remains
with T07, and the numeric demo defaults are configuration assumptions rather
than clinical or operational validation.
