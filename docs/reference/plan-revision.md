# Dev 2 planner revision handoff â€” v1

The backend supports a planner's full replacement of a DRAFT plan's request/resource selections with a recorded reason. It derives subsidy and offer costs, retains the original solver result, and records before/after choices. Revision does not reserve capacity, offers or budget. Approval revalidates the current choices before reserving anything.

## Frontend contract

1. Fetch `GET /api/v1/plans/{id}/revision-options` as planner. The response contains `contract_version: plan-revision-v1`, `version`, `input_hash`, `remaining_budget`, `current_assignments`, `resources` and `choices`.
2. Initialize the editor from `current_assignments`. Each selection is exactly `{request_id, resource_id}`. Only use opaque resource IDs returned in `choices`. A funded base unit uses an ID ending in `:funded`; an offer uses its offer ID. The persisted plan's base `resource_id` omits this suffix, so use `current_assignments` for editing.
3. Offer choice details include service date, receiving facility/site, per-request subsidy and funding inclusion. `resources` supplies units, fixed cost and exclusivity groups. Choices describe individual eligibility; a combination can exceed units, budget or shared resource limits and must be validated by submission.
4. Submit `POST /api/v1/plans/{id}/revise` with `{version, reason, assignments}` and a new `Idempotency-Key`. Assignments replace the full draft; omitted requests become unresolved. An empty list is a permitted empty plan. Reason is trimmed and must be 3â€“500 characters. Client-supplied totals, dates, subsidy and action fields are rejected.
5. Replace displayed totals and actions with the returned persisted plan. Show `decision_source: HUMAN_REVISION` and label `solver_status` as the **original solver** status; it makes no optimality claim about the human revision. `original_solver_result` and append-only `revisions` retain the comparison. The reason field should contain an operational explanation, without personal information.
6. Approve with `POST /api/v1/plans/{id}/approve`, `{version: <displayed current version>}` and a new key. Version is required after a human revision. Existing solver-only clients may still send `{}`; new UI should always send the displayed version.

Keep the edit form on a 422 error and show its returned message. A 409 `STALE_INPUT` caused by another draft edit requires refetching the draft/options; changed operational inputs require a fresh snapshot and optimization. 409 `INVALID_TRANSITION` means the draft has already been approved or closed. Do not retry an altered payload with an old idempotency key. Identical retries return their original receipt, so refetch the current plan after a retry if another edit could have occurred.

## Demo fixture and browser acceptance

Use [the versioned fixture](../../data/contracts/plan-revision-v1.json) on a fresh seed. Replace its date placeholder with `/state.config.service_date`, take the version from revision-options, and use the actual generated plan ID. It reduces the 20-request, PKR 25,000 solver plan to eight subsidy-supported requests costing PKR 8,000, with no partner/mobile actions. Approval commits PKR 8,000; the original solver output remains 20/25,000.

Check edit â†’ reason â†’ save â†’ reload â†’ approve â†’ JSON/CSV export. Check an empty reason, wrong-zone choice and two browser tabs editing the same version. Confirm the error retains editable choices and a stale approval cannot approve unseen edits. Exports include aggregate original/current/revision allocations without request identifiers; operators' scoped state omits full original/history allocations.
