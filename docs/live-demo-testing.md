# Live SEHAT GRID end-to-end checklist

This checklist follows the public-origin routing release and its optional guided demo.

Open https://sehat-grid.vercel.app. Use `demo` for each account. The compact Demo access menu selects a role and hospital, copies credentials or fills the sign-in form. Use synthetic descriptions and references throughout.

## Preparation

- Open separate tabs for `planner`, `operator-p03`, and `onboarder-p03`. Sign into each tab separately. Use Sign out when switching a tab to another account.
- Keep the app's displayed service date and current planning month selected. The seeded service date can be tomorrow; do not substitute today's date automatically.
- Write down the starting totals and take a screenshot before each workflow. Refresh the other role's tab after a change.
- Test the main planning journey before changing network quotas, budgets, ranking, participation, or eligible zones. Catalog prices/capacities are separate from primary-care referral quotas.
- At the live inspection on 10 October 2026, `pla-0001` was APPROVED: projected additional 20, cost PKR 25,000, both QUOTA-7 and MOBILE-5 PENDING_ACTIVATION. Unresolved demand was 20, confirmed 40, completed 20. All PKR 25,000 was committed. If this is still the current state, continue the existing plan; do not create another plan expecting the untouched seed result.
- State is shared between testers. Have one person drive plan changes. Browser refresh should preserve changes; a Hugging Face restart/rebuild can lose the local SQLite database. There is no public reset button. The local Docker reset commands do not reset this hosted deployment.

## Guided demo

After sign-in, click Start guided demo. Reception accounts can choose AI-assisted intake, Route / receive a request, or Offers & activation. Select a request reference for routing. Show this step opens the relevant screen and highlights its control; Next step advances the guide without taking a workflow action. The guide reads saved request/referral/plan status, explains already-reserved referrals, identifies role handoffs and resumes in the same tab. Government and onboarding accounts receive their own tours.

## 1. Government overview and hospital directory

Account: `planner`.

1. Open Network overview. Search for PIMS and select the hospital.
2. Rotate, zoom and reset the map. Clear the search and switch Capacity, Unmet demand and Funding layers.
3. Open Participating providers and select a hospital.
4. Verify the hospital name is the primary list label and detail heading, with its provider ID shown separately. Operational data remains identified as synthetic.
5. Open Monthly outcomes and Review previous month. An empty earlier month should show no recorded plan rather than inventing historical results.

Pass: map controls and hospital details work; displayed quotas and demand agree with the selected date/month; the provider list uses hospital names.

## 2. Reception: AI-assisted intake to completed care

Account: `operator-p03` (Federal Government Polyclinic).

1. Open Referral coordination. Enter `a routine visit with a family physician` into Service description.
2. Click Suggest service category. Review the General primary-care OPD suggestion explicitly. The suggestion must not authorize a request automatically.
3. Register a separate request with a unique reference such as `E2E-EAST-001`, originating provider P03, East zone and the displayed service date. Check the authorized-staff non-emergency suitability confirmation. Leave funding unneeded for this example.
4. Find providers for that request and choose Kulsum (P04). Record its available quota first. The originating hospital cannot be its own referral destination.
5. Save referral proposal, then reload and reopen Referral coordination.
6. Verify the proposal still exists and saving it did not consume quota or funding.
7. Approve & reserve proposal. Verify one slot is held and availability decreases by one.
8. Record patient agreement as P03. Sign in as operator-p04, open Receiving desk and Accept referral. Confirmation requires both decisions.
9. Record arrival, then Complete service. Reload.

Pass: the request is fulfilled, completion is recorded, the slot was consumed once, and reload preserves the result. A completed referral may leave the active referral cards; check request status and totals rather than expecting it to stay active.

## 3. Government: demand to funded resource plan

Account: `planner`.

1. Open Unresolved demand. On the untouched seed, the worked groups are eight South affordability requests, seven Central exhausted-quota requests and five North requests without an eligible partner.
2. Open Monthly planner.
3. **On the current live state:** select the existing approved `pla-0001`, inspect its assignments, actions, cost and projected coverage, then proceed to activation below.
4. **Only on a separately reset demo with an unused budget:** Create snapshot & optimize. Verify eight subsidies costing PKR 8,000, QUOTA-7 costing PKR 7,000 and MOBILE-5 costing PKR 10,000. Total: PKR 25,000 and 20 projected additional accommodations. Approve plan and reload.
5. Approval should commit funds and leave the offered resources pending activation. It must not record patients as having received care.

Pass: cost breakdown and budget agree; approval persists; projected coverage is distinct from actual confirmed/completed care. The 20/25,000 calculation is a seeded-example expectation, not a universal result after arbitrary edits.

## 4. Hospital activation and cross-hospital referral

1. Sign in as `operator-p02` (PIMS). Open Offers & activation, select the approved plan, then Confirm & activate offered resource for QUOTA-7.
2. Sign in as `operator-p08` (NORI). Activate MOBILE-5 in the same way. Verify the mobile resource/site appears.
3. Sign in as `operator-p08` (NORI). In Referral coordination, find B-01. Click Reprocess and save a reason explaining that activated PIMS quota is now available.
4. Find providers, choose P02, Save referral proposal, then Approve & reserve proposal. Record patient agreement as P08.
5. In the P02 tab, refresh and open Referral coordination. Accept the incoming referral, Record arrival and Complete service.
6. Refresh the P08 and planner tabs.

Pass: the receiving hospital sees the shared referral; neither role can skip the other's confirmation; B-01 becomes fulfilled; government post-activation confirmed/completed counts increase while the original projection remains 20.

## 5. Subsidy to completed care and government reporting

1. As `operator-p08`, find providers for A-01 and select P01 (Shifa). Only public hospitals originate new referrals in this release.
2. Save and reserve its proposal. Verify the PKR 1,000 subsidy uses the approved plan's allocation. It must not require a duplicate allocation or charge the budget twice.
3. Record patient agreement as P08. Sign in as operator-p01 to accept the incoming referral, record arrival and complete service.
4. As `planner`, open the plan's Projected versus recorded outcomes and Monthly outcomes. Export JSON and CSV summaries.
5. Check the plan ID, immutable input hash, cost breakdown and actual totals in the downloads. Aggregate exports should not expose patient/request identities.

Pass: funded care is completed and recorded once. If only B-01 and A-01 have been completed after activation, the plan should show two post-activation confirmations and completions against the projection of 20. The separate East test increases general totals, not this plan's post-activation results.

## 6. Onboarding catalog and government visibility

Account: `onboarder-p03`.

1. Open Services & prices, then Add service or test.
2. Add `Complete blood count - E2E`, category Laboratory, price PKR 900, daily service capacity 30.
3. Reload and verify it remains.
4. Edit the price to PKR 1,200 and capacity to 25. Save and reload.
5. As `planner`, refresh the P03 hospital detail and verify the saved catalog values are visible.
6. Remove the test entry after recording evidence, then confirm its removal in both roles.

Pass: create/edit/delete persist across browser reload and are shared with government. Onboarding has no patient referral or government planning controls. Adding a laboratory catalog entry does not expand the AI referral scope beyond primary care.

## 7. Failure, permission and device checks

Run these after the main journey, using separate test requests where necessary.

- Wrong password: visible login error and no access.
- Sign out and reload: protected data should require signing in again.
- Skip human service review/suitability: request creation must not succeed.
- Save then cancel an unreserved proposal: quota and funding must stay unchanged.
- Complete before acceptance/agreement/arrival: the interface/API must refuse the invalid transition.
- Role separation: reception has no government planning controls; onboarding has no patient referrals; P03 cannot manage another hospital's protected records.
- Stale edit: open the same quota record in two tabs, save in one, then save the old version in the other. Expect a conflict/review message rather than a silent overwrite. Do this after the worked planning journey because it changes network inputs.
- Temporary disconnect: switch the browser offline before a save. Expect an error rather than a success notice. Reconnect, refresh and inspect the actual saved state before retrying.
- Mobile: repeat login, intake and catalog editing on a real phone. Check scrolling, readable fields/buttons, dialogs and map fallback. Browser resizing alone does not prove physical-phone usability.

## Evidence and bug report

For each workflow record PASS/FAIL, account, date/month, request or plan ID, before/after totals and a screenshot. For failures include the exact clicks, expected result, actual result and any failed API status from browser Developer Tools → Network. Do not share session tokens or Authorization headers.

The automated browser suite is documented in [browser-acceptance.md](browser-acceptance.md). It targets a dedicated local Docker environment and resets it per case; do not point that suite at the public shared demo.
