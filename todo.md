# Scope-v1 delivery checklist

The supplied [MVP README](docs/mvp-scope-v1.md) is authoritative. The original broader daily-slot demo and optional patient portal have been superseded.

See [WORK_STATUS.md](WORK_STATUS.md) for the interruption handoff, known README gaps, and outstanding acceptance/deployment checks. Checked features below describe implemented code, not complete manual acceptance.

## Implemented

- [x] Eight synthetic providers, five Islamabad demonstration catchments, one canonical non-emergency primary-care service.
- [x] Two authenticated roles, assigned-facility authorization and attributable audit events.
- [x] Provider registration, planner participation review, service/zone declarations, dated quota and freshness.
- [x] Pinned pretrained embeddings plus fuzzy/alias/locality matching and persisted human reviews; unsupported/ambiguous outcomes.
- [x] Separate request/attempt/reservation states; independent partner response, patient agreement and funding authorization; arrival and completion.
- [x] Atomic holds, quota floor checks, cancellation cutoff, expiry, no-show and idempotent mutation receipts.
- [x] Monthly ledger with holds, commitments, settlements, releases and pool transfers.
- [x] Unique unresolved demand, reason aggregation, unknown-zone group and immutable versioned snapshots.
- [x] Real monthly OR-Tools allocation: subsidy, purchased quota and mobile clinic; dates, zones, costs, offer overlap and mobile exclusivity.
- [x] Draft revalidation; approval reserves funds/offers; operator activation changes persisted resources; rejection adjusts remaining plan.
- [x] Activated resource reprocessing; funded units avoid double subsidy charges; hospital campus coordinates are preserved when mobile sites activate.
- [x] Offline coordinate map plus optional street layer; backend quota colors and aggregate unresolved labels.
- [x] Separate projected, confirmed and completed results; aggregate JSON/CSV export with scope, assumptions, versions, costs and solver status.
- [x] Scoped operator/planner frontend screens and responsive layout.
- [x] Seed/reset, external secret configuration, migrations, pinned dependencies, combined and backend-only container recipes.
- [x] Supplied specification, architecture, API contracts, policies, two-role explanation and demo script in the repository.

## Verification evidence

- Backend workflow suite covers last-unit concurrent reservations, simultaneous monthly funding holds and plan approvals, role denial, stale reports/drafts, lifecycle approvals, cutoff/no-show, rejection/expiry/cancellation, patient decline, idempotency, non-destructive identity review and post-activation completion.
- Independent exhaustive allocation comparison: 42 tiny cases covering zero budget, overlapping quota, conflicting mobile deployment, mixed subsidy/capacity, wrong dates and stale resources; constrained greedy results also recorded.
- Matching: separate six-case development and 14-case held-out labelled sets. Small-sample results and limitations are in `outputs/matching-results.json`.
- Frontend: TypeScript, formatting and production build passed. Browser verification covered planner login, dashboard/map and allocation draft; the full operator workflow and final mobile-viewport checks remain pending.
- CI runs workflow tests on SQLite and PostgreSQL, migration drift checks, evaluation scripts, frontend checks, and an offline cold-start of the combined container.

## Deployment boundary

Public hosting remains the deployment teammate's handoff, as requested in the earlier planning messages. The repository supplies the complete container and configuration; no unrelated Railway project is changed. No patient portal, forecasting, clinical decision automation, real payments or other excluded scope is a hidden delivery task.
