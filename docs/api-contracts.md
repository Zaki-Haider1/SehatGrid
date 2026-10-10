# SEHAT GRID API contracts (target v1)

**Status:** agreed target contract for backend lanes; this is not a claim that
these routes, DTOs, policies, or workflows are implemented. Existing behavior
remains available under `/api` while clients migrate. `/api/v1` is the sole
target prefix for new clients and fixtures.

## Shared conventions

- Geography is the team-defined synthetic Islamabad pilot: zone IDs `Central`,
  `East`, `South`, `West`, and `North`. These labels and any seed centroids are
  demonstration regions, not official administrative boundaries. `zone_id` is
  an opaque string. Preserve records with unknown zones in summaries, but
  exclude them from eligible planning until reviewed.
- The only service in this MVP is `PRIMARY_CARE_OPD` (non-emergency general
  primary-care outpatient care). Service matching is a human-reviewed
  suggestion, never clinical triage or automatic clinical eligibility.
- Target provider and request IDs are opaque public strings (`FAC-P03`,
  `REQ-...` in examples); do not parse their display form. Internal database
  primary keys may remain integers. T01 adds public ID/code fields without
  requiring a destructive primary-key migration. The legacy `/api` adapter
  retains existing integer IDs and payloads during migration. Currency is
  integer PKR.
- Persist event instants as RFC 3339 UTC timestamps ending in `Z`. Interpret
  service dates, cutoff times, and calendar months in `Asia/Karachi`.
- Configurable synthetic demo defaults: capacity freshness 60 minutes; referral
  hold 15 minutes; local service-date cancellation cutoff `09:00`; service
  window ends `17:00`; limited capacity is 3 or fewer available units;
  optimizer time limit 5 seconds; authenticated session 480 minutes. A report
  is stale at age `>= 60` minutes; a hold expires at age `>= 15` minutes. The
  cutoff and service-window rule apply on the local service date. These values
  are configurable demo defaults, not validated clinical or operational policy.
  Cancellation before 09:00 on the service date releases the unit; cancellation
  at or after 09:00 forfeits it. A `CONFIRMED` attempt without recorded arrival
  by 17:00 local time becomes `NO_SHOW` and the unit is forfeited. Pending
  temporary holds expire under the hold timeout and release capacity; they do
  not become no-shows.
- The T01 seed clock is a declared reset time, overridable for reproducibility.
  Current reports are timestamped against that clock; intentionally stale
  fixtures are older than the configured freshness boundary.

## State vocabularies

Request states: `OPEN`, `IN_PROGRESS`, `UNRESOLVED`, `FULFILLED`, `CANCELLED`,
`OUT_OF_SCOPE`.

Referral-attempt states: `PROPOSED`, `AWAITING_CONFIRMATIONS`, `CONFIRMED`,
`ARRIVED`, `COMPLETED`, `REJECTED`, `CANCELLED`, `EXPIRED`, `NO_SHOW`. Attempts
are append-only history independent of request state. A failed attempt does not
erase or duplicate the unresolved request.

Plan action states: `DRAFT`, `APPROVED`, `PENDING_ACTIVATION`, `ACTIVE`,
`CLOSED`, `REJECTED`, `CANCELLED`. Ledger states: `HELD`, `COMMITTED`,
`SETTLED`, `RELEASED`; transfers link prior and successor entries and never
count an amount twice.

Facility participation states are `PENDING`, `ACTIVE`, and `SUSPENDED`. A
planner changes participation; assigned operators manage their own profiles and
services. Participation state is separate from plan action state.

## DTOs

All DTOs below describe target v1; JSON examples are in `data/contracts/`.

**Authentication** `POST /auth/login` accepts `{ "username": string,
"password": string }` and returns `{ "access_token": string,
"token_type": "bearer", "expires_at": UTC timestamp, "actor": { "actor_id":
string, "role": "OPERATOR" | "PLANNER", "facility_id": string | null } }`.
Password material is never returned.

**Facility directory** responses include `facility_id: string`,
`display_name: string`, `ownership: "PUBLIC" | "PRIVATE"`, `zone_id: string`,
nullable numeric `latitude`/`longitude`, `participation_status`, and provenance
(`origin_type`, optional source/retrieval/review fields). Profile `PATCH` accepts
only editable fields such as `display_name`, `ownership`, `zone_id`, and
coordinates; it does not accept IDs or derived capacity. Participation writes
accept `{ "status": "ACTIVE" | "SUSPENDED", "expected_version": integer,
"reason": string }` and return the status, version, actor, and UTC update time.

**Facility service** records include `facility_id: string`, `service_id:
"PRIMARY_CARE_OPD"`, `active: boolean`, `eligible_zone_ids: string[]`,
`suitability_restrictions: string[]`, `review_id: string`, `version: integer`,
and UTC update provenance. The route accepts these declared service fields;
quota is managed through the dated capacity DTO separately.

**Capacity** includes `facility_id`, `service_id`, `service_date`,
`declared_network_quota`, `held_units`, `committed_units`, `completed_units`,
`forfeited_units`, `available_units`, `updated_by`,
`updated_at`, `freshness_status` (`CURRENT`, `STALE`, `UNKNOWN`), `version`, and
`origin_type`. `committed_units` counts confirmed but uncompleted units.
Availability is quota less held, committed, completed, and forfeited units.
Availability and freshness are server-derived; clients cannot write them.
Missing or stale reports are unknown for eligibility.

**Request** includes `request_id`, `source_facility_id`, synthetic `reference`,
`zone_id`, `original_service_text`, reviewed `service_id`, nullable
`service_review_id`, `acceptable_service_dates`, staff-recorded
`in_scope_suitability`, `patient_agreement_required`, `patient_agreed`,
`funding_required`, `funding_approved`, `status`, and `unresolved_reasons`.
Requests contain no real patient details. Suitability is recorded by staff;
software does not infer clinical eligibility.

**Matching result/review** includes the original input, `model_id`, `model_revision`,
`policy_version`, candidate canonical IDs, numeric similarity scores and
supporting fields, decision (`NEEDS_REVIEW` or `NO_SUPPORTED_MATCH`), selected
canonical ID when reviewed, and reviewer actor/time. Similarity is not a
probability. T07 owns selecting a model and numeric review thresholds; the
contract exposes the configured model/revision and threshold/policy version
without claiming quality.

**Offer** includes offer/action ID, type (`SUBSIDY`, `PARTNER_QUOTA`,
`MOBILE_UNIT`), service, dates, units, eligible zones, integer-PKR cost,
`funding_included`, version, validity, and constraints. Partner quota offers
include a `spare_capacity_group_id` to prevent overlapping purchases. Mobile
offers include `mobile_unit_id` and exclusive site/date keys.

**Immutable demand snapshot** includes snapshot ID/time/hash, local calendar
month and service-date range, unique request IDs and cohorts, excluded request
IDs/reasons, and capacity/offer/rule versions. A cohort shares service, zone,
dates, suitability, and funding requirements. Unknown-zone requests remain
visible in exclusions and summaries but are ineligible until reviewed.

**Solver result** includes snapshot/budget/rule/model versions, selected
actions, request assignments, baseline and additional units, integer-PKR
cost breakdown, remaining demand, exclusions, status (`OPTIMAL`, `FEASIBLE`,
`INFEASIBLE`, `UNKNOWN`, `MODEL_INVALID`), objective, runtime, and assumptions.
`FEASIBLE` never implies `OPTIMAL`.

## Errors, authorization, concurrency, and retries

Error responses use `{ "error": { "code", "message", "retry", "details" } }`.
Stable target codes include `CAPACITY_CONFLICT`, `BUDGET_EXCEEDED`,
`STALE_INPUT`, `INVALID_TRANSITION`, `SERVICE_REVIEW_REQUIRED`,
`ROLE_FORBIDDEN`, `IDEMPOTENCY_KEY_REUSED`, `NOT_FOUND`, and `VALIDATION_ERROR`.
Conflict details identify the changed version and tell the caller to refresh,
recompute, or obtain the missing review; they must not disclose another
facility's private records.

Operators may read shared directory information and mutate only their assigned
facility and referrals they are authorized to send/receive. Planners may read
aggregate network data and manage monthly plans/participation; planner status
does not impersonate provider acceptance or patient agreement. Every mutation
is authenticated and checked against role and facility scope server-side.

Versioned writes provide `expected_version`; a mismatch returns `409
STALE_INPUT` with current version and a refresh/recompute action. Every
non-idempotent mutation accepts an `Idempotency-Key`. Repeating the same key
with the same authenticated actor, route, and canonical request body returns
the original status and response without repeating effects. Reusing that key
with a different body or route returns `409 IDEMPOTENCY_KEY_REUSED`. The key
is unique per authenticated actor; route and canonical body are recorded and
compared for replay. Records are retained for the lifetime of the affected
resource/history.

## Route ownership and fixtures

Fixtures use the route's response DTO unless marked request-only. Task IDs map
to the shared `todo.md` cards. Route ownership describes the planned target;
routes are not evidence of implementation.

| Method | Target route | Owner | Fixture / contract |
|---|---|---|---|
| POST | `/api/v1/auth/login` | T02 | Auth session contract; session default above |
| GET, POST | `/api/v1/facilities` | T03 | Capacity fixture; facility/request ID convention |
| PATCH | `/api/v1/facilities/{id}` | T03 | Facility profile + provenance contract |
| POST | `/api/v1/facilities/{id}/participation` | T03 (authorization: T02) | Facility participation state contract |
| GET, POST | `/api/v1/facilities/{id}/services` | T03 | `PRIMARY_CARE_OPD` service contract |
| PUT | `/api/v1/facilities/{id}/capacity/{service_id}/{date}` | T03 | `capacity-v1.json` |
| POST | `/api/v1/matching/facilities` | T08 | `matching-v1.json` |
| POST | `/api/v1/matching/services` | T08 | `matching-v1.json` |
| POST | `/api/v1/matching/reviews` | T08 | Matching result/review contract |
| GET, POST | `/api/v1/requests` | T05 | `eligibility-v1.json` request DTO |
| GET | `/api/v1/requests/{id}/recommendations` | T09 | `eligibility-v1.json` |
| POST | `/api/v1/referrals` | T05 | Request/attempt and capacity contracts |
| POST | `/api/v1/referrals/{id}/partner-response` | T05 | Attempt state contract |
| POST | `/api/v1/referrals/{id}/patient-agreement` | T05 | Attempt state contract |
| POST | `/api/v1/referrals/{id}/funding-approval` | T04 | Ledger state contract |
| POST | `/api/v1/referrals/{id}/arrival` | T05 | Attempt state contract |
| POST | `/api/v1/referrals/{id}/completion` | T05 | Attempt and ledger state contracts |
| POST | `/api/v1/referrals/{id}/cancel` | T05 | Attempt and capacity contracts |
| GET | `/api/v1/intelligence/summary` | T10 | `snapshot-v1.json` |
| GET | `/api/v1/intelligence/map` | T10 (display: T16) | Snapshot and capacity contracts |
| POST | `/api/v1/intelligence/snapshots` | T10 | `snapshot-v1.json` |
| GET, POST | `/api/v1/budgets` | T04 | Integer-PKR monthly budget contract |
| GET, POST | `/api/v1/partner-quota-offers` | T06 | Offer contract |
| GET, POST | `/api/v1/mobile-offers` | T06 | Offer contract |
| POST | `/api/v1/plans/optimize` | T11 | `solver-v1.json` |
| GET | `/api/v1/plans/{id}` | T11 | `solver-v1.json`; review/inspect draft before approval |
| POST | `/api/v1/plans/{id}/approve` | T12 | Action/ledger state contract |
| POST | `/api/v1/plans/{id}/actions/{action_id}/activate` | T12 | Action/ledger state contract |
| GET | `/api/v1/plans/{id}/export` | T19 | Solver result plus provenance/assumptions |
| GET | `/api/v1/audit` | T02 | Actor/time/object/reason contract |

The existing unversioned `/api` routes are a temporary compatibility surface.
The current API is not a v1 implementation and its legacy DTOs retain integer
IDs, current database states, and existing behavior. The T14 client migrates to
one `/api/v1` prefix after the target routes are implemented; no mixed-prefix
client behavior is intended. `GET /health` remains a process/database health
check outside either API prefix.

## Python imports and migration order

The behavior-preserving T00 extraction provides these current implementation
interfaces: `app.services.capacity.capacity_upsert`,
`app.services.eligibility.recommendations`,
`app.services.referrals.require/reserve/transition`,
`app.optimization.allocation.optimize`, and `app.services.plans.approve`.
`app.workflows` re-exports these names for existing imports. These functions
still implement legacy behavior and do not satisfy the target rules above.

Integration order: T00 contracts/extraction; T01 additive shared entities,
IDs, and migration/seed foundation; T02 actor/facility scope and audit; T03
provider/services/capacity versions; T04 budget ledger; T06 offers; T07 matching
model/evaluation preparation, T08 persisted matching, and T09 eligibility;
complete T05 referral lifecycle against T08/T09; then T10 snapshots, T11
optimization, T12 approval/activation, T13 independent optimizer checks, T14
UI client, and later integration/qualification cards. T01 owns model/schema/
migration changes; do not add target persistence fields as part of T00 extraction.
