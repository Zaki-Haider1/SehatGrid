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
| GET/PUT | `/referral-ranking` | Planner reads/updates the ordered `criteria` (`same_zone`, `subsidy`, `available`) with expected `version` and change `reason`; recommendations return `ranking_policy_version` |
| POST | `/requests/{id}/reprocess`, `/cancel` | Sending operator; reason; no active attempt allowed |
| POST | `/referrals` | Sending approval; request ID, capacity ID/version and facility version; atomic temporary hold |
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
| POST | `/plans/{id}/approve` | Planner; revalidate all inputs, reserve funds/offers/base earmarks |
| POST | `/plans/{id}/actions/{id}/activate` | Responsible operator; all-or-nothing offered resource activation |
| POST | `/plans/{id}/actions/{id}/reject` | Responsible operator; reason; release pending cost and update remaining plan |
| POST | `/plans/{id}/cancel` | Planner; close unspent commitments, retain settled costs |
| GET | `/plans/{id}/export?format=json` (or csv) | Planner; traceable aggregate summary without request identifiers |
| GET | `/audit` | Planner network audit / operator own events |

## Reservation example

First fetch recommendations and copy the returned versions. Submit:

```json
{"request_id":"B-01","capacity_id":"P02:PRIMARY_CARE_OPD:2026-10-11","capacity_version":3,"facility_version":1}
```

Dates and versions above are illustrative. Use the actual selected seed date and live recommendation. `CAPACITY_CONFLICT` or `STALE_INPUT` requires refreshed recommendations; do not bypass a conflict by sending an invented version.

A patient agreement, partner acceptance or funding authorization can arrive first. Only the final required approval converts held quota and funds to commitments. A receiving arrival precedes completion. All active financial state changes use the same aggregate database transaction.
