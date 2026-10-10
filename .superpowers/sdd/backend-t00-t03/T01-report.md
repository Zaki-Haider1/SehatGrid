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
