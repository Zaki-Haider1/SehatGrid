# Scope decisions and assumptions

This file records the accepted target scope and the differences between it and
the current scaffold. Target choices here coordinate later tasks; they do not
claim backend implementation, operational validation, partnerships, or health
outcomes.

## Controller rulings for T00

- The integration branch is `feat/backend-t00-t03`; T00 is the backend
  coordination/extraction owner. The existing frontend extraction remains T14.
- New client and target route prefix is `/api/v1`. Existing `/api` routes remain
  a documented compatibility surface until the client migrates; current
  endpoints do not thereby become v1 implementations.
- Keep zone IDs `Central`, `East`, `South`, `West`, and `North` for compatibility
  with existing scaffold records. In the target seed, these mean team-defined
  synthetic Islamabad pilot areas with synthetic centroids, not official
  administrative boundaries. Unknown-zone data remains visible in summaries
  and excluded from eligible planning until reviewed.
- Target service is `PRIMARY_CARE_OPD`: non-emergency general primary-care
  outpatient care. The present broad catalog and Karachi seed remain legacy
  scaffold data until the T01 seed change. Existing priority fields are not
  clinical triage.
- Demo defaults: `APP_TIMEZONE=Asia/Karachi`,
  `CAPACITY_FRESHNESS_MINUTES=60`, `REFERRAL_HOLD_MINUTES=15`,
  `CANCELLATION_CUTOFF_LOCAL=09:00`, `SERVICE_WINDOW_END_LOCAL=17:00`,
  `LIMITED_CAPACITY_THRESHOLD=3`, `OPTIMIZER_TIME_LIMIT_SECONDS=5`, and
  `AUTH_SESSION_MINUTES=480`. Freshness and hold expire at their respective
  `>=` boundaries. Cancellation before 09:00 on the local service date releases
  the unit; cancellation at/after that time forfeits it. Missing arrival by
  17:00 local time records `NO_SHOW` and forfeits the unit only for a confirmed
  attempt. Pending temporary holds expire at the hold timeout and release
  capacity without becoming no-shows. Cutoff and service window apply to the
  local service date.
  These are synthetic demo configuration values, not validated clinical or
  operational policies.
- T01's seed clock is a declared reset clock and can be overridden for
  reproducible runs. Current records use that clock; deliberately stale sample
  records predate it by more than the freshness limit.
- T07 selects the matching model and numeric threshold. Contracts expose model,
  revision, and threshold/policy version; T00 makes no accuracy or quality
  claim.

## Scope differences preserved for migration

- Current scaffold data is Karachi-oriented, with six facilities, six broad
  services, integer IDs, and legacy `pending/reserved/confirmed/completed`
  records. Target seed and target DTOs are Islamabad-oriented, use the narrow
  primary-care scope and opaque public string IDs; internal database primary
  keys may remain integers. T01 adds public ID/code fields without requiring a
  destructive primary-key migration. T00 does not rewrite seed, persistence,
  or endpoint behavior.
- The current `/api` recommendation path uses current capacity and same-zone
  preference. The target eligibility policy additionally requires active
  participation, reviewed supported service, explicit zone eligibility,
  recorded suitability, acceptable date, fresh positive capacity, funding
  readiness, and no duplicate active reservation.
- The current optimizer uses a legacy global budget, unrestricted additive
  capacity, and urgent-first objective. Target planning uses monthly integer-PKR
  ledger entries and offered subsidy, bounded partner quota, and mobile actions;
  objective order is maximize additional eligible units, minimize cost, then
  stable action IDs. T00 leaves the current solver behavior intact.
- Current approval immediately adds capacity and reprocesses pending demand.
  Target approval commits/reserves resources; partner/mobile capacity is usable
  only after operator activation.
- The current schema has neither the target request/attempt state vocabularies
  nor versioned immutable planning snapshots. T00 defines their handoff only;
  additive schema work belongs to T01 and later cards.

## Risks and limits

Synthetic zone labels/centroids are demonstration geometry and do not establish
service travel accessibility. Capacity reports and costs are simulated unless
their provenance says otherwise. Similarity is not a calibrated probability;
clinical suitability, patient consent, and provider acceptance require human
records. A `FEASIBLE` solver result is not an optimality claim. Target routes,
auth rules, idempotency, freshness enforcement, monthly ledgers, snapshots, and
solver DTOs remain proposed until their owning tasks implement and verify them.
