# Five-minute demonstration

Prepare once: install pinned dependencies, preload the model, migrate and seed/reset. Start API and frontend. Confirm `/health` and sign in. The bundled 3D city works with internet disconnected. All dates below use the date displayed in the app, not a hardcoded calendar fixture.

1. **0:00 — planner:** Network overview shows eight hospital blocks in a pale 3D city, fresh/exhausted/unknown quota, approximate sourced Islamabad positions and real hospital names with synthetic operating figures. Explain government, reception and onboarding, and the narrow routing service.
2. **0:35 — operator P03:** In Referral coordination enter `a routine visit with a family physician`, obtain a semantic suggestion, review it, and register a separate synthetic East-zone request with staff suitability checked. Choose Kulsum (P04) → Save referral proposal; refresh to show the persisted proposal consumes no quota/funds. Approve & reserve proposal, record patient agreement, then sign in as operator-p04 to accept the referral, record arrival and complete it. This separate example changes registered/completed totals but leaves the worked 20 unresolved units intact.
3. **2:00 — planner:** Unresolved demand shows eight South affordability units, seven Central exhausted-quota units and five North no-eligible-partner units. The count is unique requests, not failed attempts or the city's population.
4. **2:40 — planner:** Monthly planner → Create snapshot & optimize. Verify 8 subsidies costing PKR 8,000, QUOTA-7 costing 7,000, MOBILE-5 costing 10,000, baseline 0 and projected additional 20. Inspect assumptions and actual solver status.
5. **3:40 — planner:** Approve plan. Funds move to commitments; quota/mobile resources remain pending.
6. **4:00 — operator P02:** Offers & activation → select the approved plan → activate QUOTA-7. Operator P08 similarly activates MOBILE-5; a separate synthetic site appears.
7. **4:30 — operator P08:** Find providers for B-01 and reserve the activated quota. Record patient agreement. Operator P02 accepts, records arrival and completes it. These are synthetic demonstration events.
8. **4:50 — planner:** Compare projected additional accommodation with post-activation confirmed/completed counts. Download JSON/CSV and show the immutable snapshot hash and cost breakdown.

Use the README reset command to rehearse again. Reset is a deliberate local/CLI maintenance operation; there is no unauthenticated destructive reset route. Restarting without reset preserves records and does not fake fresh capacity.

Separate acceptance checks, outside the five-minute pitch: Funding approvals → edit the ranking order with a reason and show the resulting recommendation order/version as an operator. Monthly planner → Revise draft with reason → leave B/C requests unresolved, retaining the eight A subsidy assignments → save/reload/approve/export. This creates an eight-unit PKR 8,000 human decision with the original 20-unit/25,000 solver output preserved; it changes the worked plan and must be rehearsed after a separate reset. [Browser acceptance](browser-acceptance.md) automates both flows and the unchanged 8/7/5 pitch independently.

## Three-interface design walkthrough

Start as `planner` in Network overview. Orbit/zoom the pale 3D city, search PIMS, select its hospital block, switch capacity/demand/funding layers and open Monthly outcomes. Review the previous month explicitly: a freshly seeded demo has no prior-month records. Budgets and ranking policy remain in Monthly planner and Funding approvals.

Sign in as `operator-p03` for the reception desk, incoming/outgoing referral cards and reviewed intake. Sign in as `onboarder-p03` for Hospital setup and Services & prices: add a laboratory test with a declared price/capacity, reload, edit it, and verify that the government hospital detail sees the saved catalog. The onboarding account has no patient referrals or government actions. Catalog tests do not expand the primary-care routing scope.

The operational five-minute acceptance journey and the additional design/catalog checks are separate reproducible browser cases; see `docs/browser-acceptance.md`.

## Patient-message and routing extension

In a public reception account, register a reviewed request with consent and a synthetic international-format number. Optionally specify exact catalog test names. Open the patient-message demo in a second tab. Reserve the referral, record receiving acceptance and patient agreement (plus funding approval if needed); the confirmation appears in the chat. Cancel it from the sending hospital and reprocess to a new eligible destination: the chat shows cancellation and then the new confirmation. It is explicitly a simulation with no WhatsApp delivery. Private receptionists use Receiving desk and cannot create outgoing requests.

In Government / Funding approvals, inspect Hospital routing points, change a preference with a reason, and refresh recommendations to see the score. Use Onboarding / Services & prices to maintain tests, prices and daily capacity. See [the implementation notes](routing-and-patient-updates.md).
