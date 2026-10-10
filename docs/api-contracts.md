# API contracts — implemented scope v1

Base path: `/api/v1`. `GET /health` is public. All other routes except `POST /auth/login` require `Authorization: Bearer <JWT>`. All mutations require an `Idempotency-Key` of 8–160 characters. Reuse the same key and identical payload for a retry; a different payload with that key returns `IDEMPOTENCY_CONFLICT`. Login is exempt.

Errors use `{ "detail": { "code": "STALE_INPUT", "message": "Refresh…" } }`. Validation errors are 422, unauthorized authentication 401, role/scope denial 403, missing entities 404, workflow/version conflicts 409. The UI displays corrective messages and retains the form for correction.

The Pydantic input contracts live in `backend/app/mvp/schemas.py`. All inputs forbid unknown fields. The dispatcher uses the explicit routes below; `/docs` shows its shared transport route rather than pretending each dynamic operation has a separately generated OpenAPI schema.

| Method | Route | Permission / contract |
|---|---|---|
| POST | `/auth/login` | `username`, `password`; seeded account JWT |
| GET | `/auth/me` | Current actor and facility assignments |
| GET | `/state?month=YYYY-MM&date=YYYY-MM-DD` | Role-scoped UI projection; backend totals only |
| GET/POST | `/facilities` | Directory / reception or onboarder registration, initially pending |
| PATCH | `/facilities/{id}` | Assigned onboarder or legacy operator; full permitted profile and expected `version` |
| POST | `/facilities/{id}/participation` | Planner; status, expected version, reason |
| GET/POST | `/facilities/{id}/services` | Reviewed primary-care category, eligible zones, subsidy rule; assigned onboarder or legacy operator writes |
| PUT | `/facilities/{id}/capacity/PRIMARY_CARE_OPD/{date}` | Assigned onboarder or legacy operator; `quota`, expected `version` (0 to create) |
| POST | `/facilities/{id}/catalog` | Assigned onboarder only; service/test fields and expected facility version |
| PATCH/DELETE | `/facilities/{id}/catalog/{item_id}` | Assigned onboarder only; full service/test fields and expected facility version |
| GET | `/services` | Single in-scope canonical service |
| POST | `/matching/services`, `/matching/facilities` | Original `text`, optional locality/type evidence |
| POST | `/matching/reviews` | `match_id`, ACCEPT/CORRECT/DECLINE, canonical candidate, reason, optional existing record ID; actor/scope checks |
| GET/POST | `/requests` | Own/incoming queue / synthetic request intake with stored review ID and human suitability flags |
| GET | `/requests/{id}/recommendations` | Sending operator; eligibility explanations and input versions |
| GET/PUT | `/referral-ranking` | Planner reads/updates an ordered permutation of `same_zone`, `subsidy`, and `available` with expected `version` and change `reason`; this changes order only, never eligibility. Recommendations return `ranking_policy_version`. |
| POST | `/requests/{id}/reprocess`, `/cancel` | Sending operator; reason; no active attempt allowed |
| POST | `/referrals`, `/referrals/proposals` | Sending operator; request ID, capacity ID/version and facility version; persists a `PROPOSED` attempt without holding capacity or funds. `/referrals/proposals` is an alias; both routes are proposal-only. |
| POST | `/referrals/{id}/reserve` | Sending operator; empty body; rechecks the selected candidate and atomically advances `PROPOSED` to `AWAITING_CONFIRMATIONS`, creating the temporary capacity/funding hold |
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

## Onboarding catalog

`POST /facilities/P03/catalog` creates an entry; `PATCH` and `DELETE /facilities/P03/catalog/{item_id}` use the same input shape. Each operation requires the assigned `onboarder` JWT and an idempotency key. Reads are included in the facility's `catalog` within `/state`. The response is the updated facility with its incremented `version` and catalog; all mutations record `CATALOG_UPDATED` audit history.

```json
{
  "name": "Complete blood count",
  "category": "Laboratory",
  "price": 900,
  "daily_capacity": 30,
  "active": true,
  "version": 1
}
```

Use the current facility version and omit the catalog item's `id` from the body. Categories are Consultation/Laboratory/Imaging/Other; name is 2–120 characters, integer PKR price is 0–10,000,000, and declared daily capacity is 0–10,000. A facility supports up to 200 entries. Stale versions return `STALE_INPUT`; wrong role/facility returns 403. Configured cross-origin hosts may preflight `DELETE` with Authorization/Content-Type/Idempotency-Key. Catalog services are informational and do not expand automated primary-care routing eligibility or quota.

Onboarders receive no requests, referrals, plans, aggregate network summary, ledger, budget or subsidy rule in `/state`. Profile/service/quota routes retain legacy operator compatibility; catalog mutation remains onboarding-only.

## Proposal-first referral example

Draft revision examples, error recovery and Dev 3's UI fixture are in [the plan revision handoff](dev2-plan-revision.md). Original solver output remains immutable; `decision_source` identifies human decisions in the plan and aggregate JSON/CSV exports.

First fetch recommendations and copy the returned versions. Submit:

```json
{"request_id":"B-01","capacity_id":"P02:PRIMARY_CARE_OPD:2026-10-11","capacity_version":3,"facility_version":1}
```

Dates and versions above are illustrative. Use the actual selected seed date and live recommendation. `CAPACITY_CONFLICT` or `STALE_INPUT` requires refreshed recommendations; do not bypass a conflict by sending an invented version.
`POST /referrals` persists this as `PROPOSED`; it does not reserve capacity or funds. The selected attempt is visible in the role-scoped `GET /state` response before the sender chooses to reserve it.

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

Use the selected candidate and its versions from `GET /requests/{id}/recommendations`. The current UI should call `POST /referrals`; `/referrals/proposals` is a proposal-only alias for clients that adopted that path earlier.

```http
POST /api/v1/referrals
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

There is no `expires_at` until reservation. The request remains `OPEN` and appears as unresolved demand; the proposal blocks a second active attempt for that request. Refresh `GET /state` to recover the persisted attempt in the role-scoped `referrals` list. Capacity held/committed/completed counts, package-funded units, reservations, subsidy ledger entries and budget totals do not change. The sender can cancel a proposal through `POST /referrals/{id}/cancel`; cancellation keeps it in history and reopens the request without a resource effect.

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

The returned attempt keeps its ID and advances to `AWAITING_CONFIRMATIONS`, with `expires_at`, `capacity_version_at_hold`, and `facility_version_at_hold`. If the proposal's capacity or facility version changed, its capacity became stale, or the selected candidate is no longer eligible, it advances to `EXPIRED` instead; this response has no `expires_at`, capacity hold, reservation or ledger entry. A stale proposal also expires when a GET refreshes state or recommendations. In either case the request is refreshed and the sender can choose from current recommendations. Current subsidy terms and authorization requirements are recalculated at reservation time.

Example reserve response (dynamic IDs, timestamps, amounts and versions come from the selected request):

```json
{
  "id": "ref-0001",
  "request_id": "B-01",
  "facility_id": "P02",
  "capacity_id": "P02:PRIMARY_CARE_OPD:2026-10-11",
  "date": "2026-10-11",
  "status": "AWAITING_CONFIRMATIONS",
  "partner_accepted": false,
  "patient_agreed": false,
  "funding_approved": true,
  "subsidy": 0,
  "package_funded": false,
  "ledger_id": null,
  "plan_id": null,
  "created_at": "<UTC timestamp>",
  "version": 2,
  "policy_version": "same-zone-cost-capacity-id-v1",
  "ranking_policy_version": "referral-ranking-v1",
  "capacity_version_at_proposal": 3,
  "facility_version_at_proposal": 1,
  "proposed_by": "operator-p01",
  "expires_at": "<UTC timestamp>",
  "capacity_version_at_hold": 3,
  "facility_version_at_hold": 1
}
```

If input versions are stale, reserve instead returns the same attempt with a response like this; refresh `GET /requests/{id}/recommendations`, then create a new proposal:

```json
{
  "id": "ref-0001",
  "request_id": "B-01",
  "status": "EXPIRED",
  "reason": "Proposal inputs changed; refresh recommendations",
  "version": 2
}
```

To abandon a current proposal, call:

```http
POST /api/v1/referrals/ref-0001/cancel
Authorization: Bearer <sending operator JWT>
Idempotency-Key: cancel-ref-0001
Content-Type: application/json
```

```json
{"reason":"Sender chose another provider"}
```

The response keeps the attempt in history with `status: "CANCELLED"` and the supplied `reason`; it creates no reservation or ledger entry. Representative response fields:

```json
{
  "id": "ref-0001",
  "request_id": "B-01",
  "status": "CANCELLED",
  "reason": "Sender chose another provider",
  "version": 2,
  "updated_at": "<UTC timestamp>"
}
```

A new proposal can then be created if the request is still eligible.

All three mutations require an idempotency key. Repeating the same key and request returns the original response. A proposal does not authorize partner/patient/funding confirmation; those existing transitions remain available only after reservation.

A patient agreement, partner acceptance or funding authorization can arrive first. Only the final required approval converts held quota and funds to commitments. A receiving arrival precedes completion. All active financial state changes use the same aggregate database transaction.

## Public-origin routing and message-preview extension

`POST requests` additionally accepts `required_tests: string[]` (up to 20), `whatsapp_phone` (optional E.164 international number), and `whatsapp_consent: boolean`. Consent is required to store a phone number. Required tests match normalized catalog names. The authenticated source must be an assigned, active public hospital. Private-source attempts return `PUBLIC_SENDER_REQUIRED` (403); a private hospital is still a valid receiving destination. Self-referrals are excluded. Older operator-p01 sending examples above are historical; fresh-seed outgoing requests now use public operator-p08.

`PUT facilities/{id}/routing-points` is planner-only and takes `{points: 0..100, version: facilityVersion, reason: string}`. Recommendations include `routing_score` and `routing_points`, sorted by the continuous capacity/preference score before existing tie-break criteria. A hospital profile cannot change its registered ownership.

`GET state` includes facility `routing_points` and `routing_metrics` (referral count, completed count, closed-referral completion rate), plus authorized reception `notifications`. Notification fields include id, request_id, referral_id, event, masked recipient, message, created_at and status `PREVIEW_ONLY`. Confirmation and cancellation persist previews transactionally, deduplicated by referral/event. There is no live transport or delivery receipt. See [routing and patient updates](routing-and-patient-updates.md) for all invariants.
