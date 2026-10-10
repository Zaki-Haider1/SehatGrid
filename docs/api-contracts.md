# API contracts — implemented scope v1

Base path: `/api/v1`. `GET /health` is public. All other routes except `POST /auth/login` require `Authorization: Bearer <JWT>`. All mutations require an `Idempotency-Key` of 8–160 characters. Reuse the same key and identical payload for a retry; a different payload with that key returns `IDEMPOTENCY_CONFLICT`. Login is exempt.

Errors use `{ "detail": { "code": "STALE_INPUT", "message": "Refresh…" } }`. Validation errors are 422, unauthorized authentication 401, role/scope denial 403, missing entities 404, workflow/version conflicts 409. The UI displays corrective messages and retains the form for correction.

The Pydantic input contracts live in `backend/app/mvp/schemas.py`. All inputs forbid unknown fields. The dispatcher uses the explicit routes below; `/docs` shows its shared transport route rather than pretending each dynamic operation has a separately generated OpenAPI schema.

| Method | Route | Permission / contract |
|---|---|---|
| POST | `/auth/login` | `username`, `password`; seeded account JWT |
| GET | `/auth/me` | Current actor and facility assignments |
| GET | `/state?month=YYYY-MM&date=YYYY-MM-DD` | Role-scoped UI projection; backend totals only |
| GET/POST | `/facilities` | Directory / operator registration, initially pending |
| PATCH | `/facilities/{id}` | Assigned operator; full permitted profile and expected `version` |
| POST | `/facilities/{id}/participation` | Planner; status, expected version, reason |
| GET/POST | `/facilities/{id}/services` | Reviewed primary-care category, eligible zones, subsidy rule; own operator writes |
| PUT | `/facilities/{id}/capacity/PRIMARY_CARE_OPD/{date}` | Own operator; `quota`, expected `version` (0 to create) |
| GET | `/services` | Single in-scope canonical service |
| POST | `/matching/services`, `/matching/facilities` | Original `text`, optional locality/type evidence |
| POST | `/matching/reviews` | `match_id`, ACCEPT/CORRECT/DECLINE, canonical candidate, reason, optional existing record ID; actor/scope checks |
| GET/POST | `/requests` | Own/incoming queue / synthetic request intake with stored review ID and human suitability flags |
| GET | `/requests/{id}/recommendations` | Sending operator; eligibility explanations and input versions |
| GET/PUT | `/referral-ranking` | Planner reads/updates an ordered permutation of `same_zone`, `subsidy`, and `available` with expected `version` and change `reason`; this changes order only, never eligibility. Recommendations return `ranking_policy_version`. |
| POST | `/requests/{id}/reprocess`, `/cancel` | Sending operator; reason; no active attempt allowed |
| POST | `/referrals/proposals` | Sending operator; request ID, capacity ID/version and facility version; persists a `PROPOSED` attempt without holding capacity or funds |
| POST | `/referrals/{id}/reserve` | Sending operator; empty body; rechecks the selected candidate and atomically advances `PROPOSED` to `AWAITING_CONFIRMATIONS`, creating the temporary capacity/funding hold |
| POST | `/referrals` | Legacy direct-reservation operation; sending approval with request ID, capacity ID/version and facility version; atomic temporary hold |
| POST | `/referrals/{id}/partner-response` | Receiving operator; accepted boolean and rejection reason |
| POST | `/referrals/{id}/patient-agreement` | Sending/receiving operator; independent recorded agreement |
| POST | `/referrals/{id}/funding-approval` | Planner; accepted boolean; operator funding delegation is deliberately zero |
| POST | `/referrals/{id}/arrival`, `/completion` | Receiving operator; valid predecessor required |
| POST | `/referrals/{id}/cancel`, `/no-show` | Reason, actor scope and cutoff/date checks |
| GET | `/intelligence/summary`, `/intelligence/map` | Planner aggregate current counts; no request details in map |
| POST | `/intelligence/snapshots` | Planner; selected month; immutable input snapshot |
| GET | `/intelligence/snapshots/{id}` | Planner; preserved decision input |
| GET/POST | `/budgets` | Planner writes selected month, integer authorized amount and expected version |
| POST | `/subsidy-rules` | Planner; month, fixed integer amount, expected version |
| GET/POST | `/partner-quota-offers`, `/mobile-offers` | Scoped offers; owned facility, date, zones, capacity/cost and explicit shared spare group or mobile unit/site |
| POST | `/plans/optimize` | Planner; immutable snapshot ID |
| GET | `/plans/{id}` | Planner; draft/status, assignments, assumptions, solver result |
| GET | `/plans/{id}/revision-options` | Planner, current draft; `plan-revision-v1` selections, eligibility choices and current version |
| POST | `/plans/{id}/revise` | Planner, current draft; expected `version`, recorded `reason`, full `assignments` of `{request_id, resource_id}`; server-derived totals |
| POST | `/plans/{id}/approve` | Planner; current `version` required after human revision; revalidate all inputs/selections, reserve funds/offers/base earmarks |
| POST | `/plans/{id}/actions/{id}/activate` | Responsible operator; all-or-nothing offered resource activation |
| POST | `/plans/{id}/actions/{id}/reject` | Responsible operator; reason; release pending cost and update remaining plan |
| POST | `/plans/{id}/cancel` | Planner; close unspent commitments, retain settled costs |
| GET | `/plans/{id}/export?format=json` (or csv) | Planner; traceable aggregate summary without request identifiers |
| GET | `/audit` | Planner network audit / operator own events |

## Reservation example

Draft revision examples, error recovery and Dev 3's UI fixture are in [the plan revision handoff](dev2-plan-revision.md). Original solver output remains immutable; `decision_source` identifies human decisions in the plan and aggregate JSON/CSV exports.

First fetch recommendations and copy the returned versions. Submit:

```json
{"request_id":"B-01","capacity_id":"P02:PRIMARY_CARE_OPD:2026-10-11","capacity_version":3,"facility_version":1}
```

Dates and versions above are illustrative. Use the actual selected seed date and live recommendation. `CAPACITY_CONFLICT` or `STALE_INPUT` requires refreshed recommendations; do not bypass a conflict by sending an invented version.
This body is for the legacy direct `POST /referrals` route. New operator controls should use the proposal-first sequence below so the selected attempt is visible before reservation.

## Planner referral ranking

`GET /referral-ranking` is planner-only and returns the persisted versioned ordering:

```json
{
  "criteria": ["same_zone", "subsidy", "available"],
  "version": 1,
  "policy_version": "referral-ranking-v1"
}
```

Update all three criteria exactly once. `version` is an optimistic concurrency check; a stale update returns `STALE_INPUT`. `reason` is required and audited.

```http
PUT /api/v1/referral-ranking
Authorization: Bearer <planner JWT>
Idempotency-Key: ranking-policy-v2
Content-Type: application/json
```

```json
{
  "criteria": ["subsidy", "same_zone", "available"],
  "version": 1,
  "reason": "Prefer lower subsidy before zone proximity"
}
```

The response returns `version: 2` and `policy_version: "referral-ranking-v2"`. A recommendation includes that exact value as `ranking_policy_version`. The criteria sort candidates only after all existing service, suitability, zone, date, freshness, capacity, and funding checks pass. Stable facility ID and date break remaining ties.

Recommendation response shape (string values, dates, and counts depend on the live seed):

```json
{
  "candidates": [
    {
      "facility_id": "P02",
      "name": "Example Clinic",
      "capacity_id": "P02:PRIMARY_CARE_OPD:2026-10-11",
      "date": "2026-10-11",
      "available": 2,
      "capacity_version": 3,
      "facility_version": 1,
      "subsidy": 0,
      "package_funded": false,
      "same_zone": true,
      "policy_version": "same-zone-cost-capacity-id-v1",
      "ranking_policy_version": "referral-ranking-v2",
      "plan_id": null,
      "funding_authorization_required": false,
      "explanation": "Reviewed primary-care service; declared zone eligibility; 2 eligible units (including any reserved plan unit). Receiving acceptance and patient agreement required."
    }
  ],
  "ranking_policy_version": "referral-ranking-v2",
  "reasons": [],
  "policy_version": "same-zone-cost-capacity-id-v1"
}
```

## Proposed referral attempt

Use the selected candidate and its versions from `GET /requests/{id}/recommendations`. The same payload applies to proposal creation:

```http
POST /api/v1/referrals/proposals
Authorization: Bearer <sending operator JWT>
Idempotency-Key: proposal-B-01
Content-Type: application/json
```

```json
{
  "request_id": "B-01",
  "capacity_id": "P02:PRIMARY_CARE_OPD:2026-10-11",
  "capacity_version": 3,
  "facility_version": 1
}
```

The response is a persisted referral attempt; representative fields are:

```json
{
  "id": "ref-0001",
  "request_id": "B-01",
  "facility_id": "P02",
  "capacity_id": "P02:PRIMARY_CARE_OPD:2026-10-11",
  "date": "2026-10-11",
  "status": "PROPOSED",
  "partner_accepted": false,
  "patient_agreed": false,
  "funding_approved": true,
  "subsidy": 0,
  "package_funded": false,
  "ledger_id": null,
  "plan_id": null,
  "created_at": "<UTC timestamp>",
  "version": 1,
  "policy_version": "same-zone-cost-capacity-id-v1",
  "ranking_policy_version": "referral-ranking-v1",
  "capacity_version_at_proposal": 3,
  "facility_version_at_proposal": 1,
  "proposed_by": "operator-p01"
}
```

There is no `expires_at` until reservation. The request remains `OPEN` and appears as unresolved demand; the proposal blocks a second active attempt for that request. Refresh `GET /state` to recover the persisted attempt in the role-scoped `referrals` list. Capacity held/committed/completed counts, package-funded units, reservations, subsidy ledger entries and budget totals do not change. A proposal remains until cancelled or reserved; only the subsequent reservation hold has an expiry.

The sender can reserve the same attempt after a fresh server-side eligibility/version check:

```http
POST /api/v1/referrals/ref-0001/reserve
Authorization: Bearer <sending operator JWT>
Idempotency-Key: reserve-ref-0001
Content-Type: application/json
```

```json
{}
```

The returned attempt keeps its ID and advances to `AWAITING_CONFIRMATIONS`, with `expires_at`, `capacity_version_at_hold`, and `facility_version_at_hold`. A stale capacity/facility version or newly ineligible provider returns `STALE_INPUT` or `CAPACITY_CONFLICT`; the attempt remains `PROPOSED` and no hold is created. Current subsidy terms and authorization requirements are also recalculated at reservation time. Cancellation uses the existing `POST /referrals/{id}/cancel` route with `{"reason":"Sender chose another provider"}` and leaves the proposal in history without a resource effect.

All three mutations require an idempotency key. Repeating the same key and request returns the original response. A proposal does not authorize partner/patient/funding confirmation; those existing transitions remain available only after reservation.

A patient agreement, partner acceptance or funding authorization can arrive first. Only the final required approval converts held quota and funds to commitments. A receiving arrival precedes completion. All active financial state changes use the same aggregate database transaction.
