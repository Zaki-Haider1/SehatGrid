# T01 report: schema and seed foundation

Status: **PASS**

## RED

The new seed and migration tests were run before implementing their models and
seed data:

```powershell
.venv/Scripts/python -m pytest backend/tests/test_seed.py backend/tests/test_migrations.py -q
```

The expected initial failures showed missing shared entities (`Zone` and the
other target models), target seed rows, and the additive migration. During
schema verification, named-check assertions also caught that Alembic's batch
`table_args` did not create the expected checks. The migration was changed to
create them explicitly; the original capacity nonnegative guard was explicitly
recreated as a named constraint as well.

## GREEN

Focused migration and seed verification, with both SQLite and the isolated
PostgreSQL test schemas enabled:

```powershell
$env:TEST_DATABASE_URL='<isolated test database URL>'
.venv/Scripts/python -m pytest backend/tests/test_migrations.py backend/tests/test_seed.py -q
```

Result: **10 passed**. The migration test applies Alembic to a fresh database,
then independently upgrades a database containing legacy facility, service,
capacity, request, referral, budget, and plan rows. It checks preserved integer
IDs, generated stable public IDs, legacy status/FK values, linked referral
history, committed budget, required tables/columns, nullable request service,
and named schema checks on SQLite and PostgreSQL.

Final required gate:

```powershell
$env:TEST_DATABASE_URL='<isolated test database URL>'
.venv/Scripts/python -m pytest -q backend/tests
.venv/Scripts/ruff.exe check backend
```

Result: **46 passed** and **All checks passed!** The test run reports existing
Starlette/Alembic deprecations and SQLite notices that unnamed legacy checks
are replaced by explicit named checks. `git diff --check` was also run; no
whitespace errors remain.

## Schema and seed

- Added additive revision `3f36031db108`; the initial migration
  `763866885016` is unchanged. Integer primary keys remain intact; stable
  opaque public IDs are backfilled for existing facilities, services, and
  requests. Legacy facility participation backfills to `PENDING`, ownership
  remains unknown (`NULL`), legacy service text review is `NEEDS_REVIEW`, and
  old capacity freshness is `UNKNOWN`.
- Added the shared identity/zone, facility service and participation history,
  capacity reservation, referral attempt, match review, monthly budget and
  ledger, subsidy/offer, snapshot/plan action, audit, and seed metadata tables.
  Capacity keeps one aggregate: `reserved`, `consumed`, and `forfeited_units`;
  held/committed/completed DTO values are derived from reservation/attempt
  history. Requests retain one nullable `service_id` and one `status` column.
- Product seed is limited to five synthetic Islamabad zones, eight active
  synthetic providers, one `PRIMARY_CARE_OPD` service, report freshness and
  exhaustion examples, and 20 disjoint unresolved requests split 8/7/5.
  It persists a PKR 25,000 monthly budget, PKR 1,000/unit subsidy eligibility,
  quota/mobile offers, and explicit source exclusions. It creates no plan or
  computed solver output. Unsupported-service exclusion stores `service_id`
  as `NULL`.
- Seed clock is injectable and stored in metadata. Repeated default seed is
  idempotent; explicit reset refreshes the target seed and uses the stored
  budget ID so similarly sized unrelated budgets survive. Broader legacy data
  for compatibility API tests now lives only in `backend/tests/seed_helpers.py`.
- Updated API contract and assumptions for legacy-to-v1 request-state mapping,
  review-gated historical service FKs, nullable unsupported service, and the
  single stored capacity aggregate.

## Files

- `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/seed.py`
- `backend/migrations/env.py`,
  `backend/migrations/versions/3f36031db108_t01_shared_schema_foundation.py`
- `backend/tests/conftest.py`, `backend/tests/__init__.py`,
  `backend/tests/seed_helpers.py`, `backend/tests/test_seed.py`,
  `backend/tests/test_migrations.py`
- `docs/api-contracts.md`, `docs/assumptions.md`

## Limitations

This task provides schema and deterministic seed foundation only. It does not
implement authorization, request/referral workflows, computed freshness,
solver output, plan approval/activation, or target APIs. Schema upgrades were
verified on SQLite and PostgreSQL; migration downgrade behavior was not part of
the acceptance checks.

## Review round 1

The review identified six load-bearing gaps: cohort facts were not matchable from the persisted zone/capacity/offer records; reviewed service references were dangling or mislabeled as model output; reset could erase unrelated data or stop without rebuilding; the seed fixture/CLI controls were absent; model status widths drifted from the existing database; and migration tests did not require Alembic autogenerate parity. The round also rechecked linked-history reset behavior and packaging of the versioned fixture.

### RED evidence

- The pre-fix migration parity check on fresh SQLite and PostgreSQL databases raised `AutogenerateDiffsDetected` for `care_requests.status`, `referrals.status`, and `allocation_plans.status` (`VARCHAR(20)` in the database versus `String(24)` in the models).
- The first linked-activity reset regression run exposed a `TypeError` in the plan-action activity predicate before reset could return a controlled response. The predicate was parenthesized and the API now translates the preflight conflict to HTTP 409.
- Review findings documented the missing source fixture/CLI flags, false review provenance, and persisted cohort mismatches; tests now assert their actual source rows rather than aggregate counts alone.

### GREEN evidence

Focused review-round checks:

```powershell
$env:TEST_DATABASE_URL='<isolated PostgreSQL test URL>'
.venv/Scripts/python -m pytest backend/tests/test_seed.py backend/tests/test_seed_cli.py backend/tests/test_workflows.py backend/tests/test_migrations.py -q
```

Result: **62 passed** across SQLite and PostgreSQL. Migration tests apply Alembic to fresh and populated legacy databases, preserve integer IDs and linked referral/capacity/request history, and run `alembic.command.check` after each upgrade. Seed tests derive all three cohort facts from provider-service, capacity, subsidy, quota, mobile-site, date, and funding rows; they also check manual review provenance and idempotent reset behavior. The API reset test creates linked referral activity and an unrelated request referencing a demo facility, then verifies HTTP 409 and that all referenced rows and seed metadata remain present.

Packaging checks passed: `docker compose config -q`; a root-context Docker image build; and an import/read smoke test from the built image, resolving the fixture at `/app/data/seed/primary-care-demo-v1.json`.

Final gates after the last code change:

```powershell
$env:TEST_DATABASE_URL='<isolated PostgreSQL test URL>'
.venv/Scripts/python -m pytest -q backend/tests
.venv/Scripts/ruff.exe check backend
```

Result: **62 passed** and **All checks passed!** Existing Starlette and Alembic deprecation notices remain, along with SQLite warnings about unnamed legacy checks during batch recreation. `git diff --check` passed.

### Round 1 files and limits

Added `data/seed/primary-care-demo-v1.json`, `backend/tests/test_seed_cli.py`, and updates to `backend/app/seed.py`, `backend/app/seed_cli.py`, `backend/app/main.py`, `backend/app/models.py`, migration/seed/workflow tests, `backend/Dockerfile`, `docker-compose.yml`, `backend/railway.toml`, and `docs/deployment.md`. The seed CLI requires the explicit pair `--reset --disposable-demo` for destructive demo reset and accepts an injected day and timezone-aware clock. Reset now rebuilds only fixture-owned rows, preserves unrelated records, and refuses linked application activity before any delete. The primary migration downgrade still has deferred placeholders and was not run as an acceptance gate.
