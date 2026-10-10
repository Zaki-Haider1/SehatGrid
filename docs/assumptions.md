# Operational policies and limits

- Scope: non-emergency general primary-care OPD; recorded external suitability is mandatory. No patient identifiers beyond synthetic references.
- Time: UTC event timestamps; Asia/Karachi date/month display and accounting. Capacity is a daily network commitment, not an appointment time or total hospital throughput.
- Freshness: 1,440 minutes by default. Missing, suspended or stale quota is unknown. A new update is explicit; unused units do not roll forward.
- Temporary holds: 30 minutes by default, expired transactionally when the API next reads/writes the network. No background scheduler is needed for correctness at access time.
- Cancellation: before 09:00 PKT on the service date releases confirmed quota; at/after this cutoff forfeits it. Temporary hold expiry always releases. No-show is only accepted after the service date and forfeits quota. Completion never releases quota.
- Funding: integer PKR. HELD, COMMITTED and SETTLED each consume budget exactly once. RELEASED is retained history. A pool-to-referral transfer reduces the pool before creating the referral entry. Fixed resource costs settle once on activation. Funding-included units remain usable without another subsidy after unassigned earmarks are released.
- Subsidy schedule: a versioned fixed primary-care contribution for the selected month. Seed value PKR 1,000 is synthetic. It is not a verified treatment tariff.
- Plan expiry: after the latest selected service date, unused earmarks and pending commitments are released on the next API access. Explicit plan closure is available earlier. Pending actions can be rejected by their responsible operator, updating remaining cost, benefit and ledger commitments. Packages activate all-or-nothing.
- Plans reserve base-capacity earmarks in held units; referral reservation transfers that earmark without a second capacity charge. Pending quota/mobile offers cannot be used before activation.
- Overlap: a shared spare-capacity group/date can be purchased once; a mobile unit/date can occupy one site. Fixed offers are immutable once posted except their lifecycle; publish a fresh dated offer for changed terms.
- Request identity: one active attempt per request; failed attempts do not duplicate demand. Patient-declined requests remain excluded from funding planning until the operator records reprocessing.
- Geography: five team-defined catchments. Public directory names/campus points are context only. All partner agreements, capacity, funding and requests are synthetic. The mobile site is separate from the host's public campus.
- Snapshots are immutable. Capacity, participation, request, offer, budget and ledger changes invalidate draft approvals. Conservative network-wide input hashing can require recomputation after an unrelated pilot update.
- Matching: pretrained embeddings, exact aliases, fuzzy score and locality/type checks. Every merge/category decision is human reviewed; unsupported text is not automatically assigned. Original IDs and records remain.
- Results: projected allocation, confirmation and completion are separate. The displayed current confirmation denominator includes pending cases and is not advertised as a mature-cohort completion rate.
- Exports contain aggregate zone/resource allocations, source versions, assumptions, costs and solver status; they do not expose synthetic request identifiers.
- Small-count suppression and real-data sharing are not enabled: this application only seeds synthetic requests. Real use requires a separate governance and onboarding phase.
