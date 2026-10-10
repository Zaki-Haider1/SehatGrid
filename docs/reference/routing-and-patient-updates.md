# Routing and patient updates

This revision implements the October 10 product requirements. Public hospitals may refer to public or private destinations. A private hospital may receive and manage referrals but may not originate or manually reroute them. A referral still needs sending approval, receiving acceptance, patient agreement and any required funding authorization before it becomes confirmed.

## Permissions

Username/password authentication routes to the account's stored role. Public receptionists register requests, review recommendations, reserve proposals and reprocess cancelled referrals. Private receptionists accept/reject incoming referrals, record agreement, arrival, completion and cancellation, and contact the sending hospital for a replacement destination. API checks enforce the restriction, independently of hidden frontend controls. Staff cannot edit a hospital's registered ownership to gain sending privileges. Newly registered hospitals remain pending until government approval.

Government representatives manage participation, budgets and hospital preference points. Onboarders manage their assigned hospital profiles, reviewed primary-care eligibility, dated network quotas and service catalogs. Existing records keep their original source; old private-origin demo requests cannot be newly routed under the updated rules. Fresh demo seeds originate requests at public NORI (operator-p08), preserving the existing receiving hospitals and allocation example.

## Continuous routing and government points

Every recommendation first checks reviewed service eligibility, active participation, geography, requested date, fresh capacity, funding and required tests. The source hospital is excluded as a referral destination. There is no condition requiring the sending hospital to be full.

Eligible destinations receive `60 × remaining quota / total quota + 0.4 × government preference points`. Government points range from 0 to 100, default to 50, require a reason and are recorded in the audit trail. The score is recalculated after reservations, completions and capacity changes, so pressure progressively shifts recommendations toward hospitals with room. Existing government-controlled location/subsidy/available-capacity criteria resolve score ties, followed by stable hospital/date identifiers. Points never override eligibility. A score of zero is not a ban; suspension is the explicit exclusion control.

The government panel also shows referral count, completed count and completion percentage among closed referrals (completed, rejected, cancelled and no-show). These are descriptive platform metrics, not clinical quality ratings. Low sample sizes and patient cancellations affect them; preference points are an explicit government decision rather than an automatic claim of quality.

The monthly optimizer retains its maximum-coverage, then minimum-cost objective. Hospital preference points govern day-to-day recommendations, not the budget optimizer's objective. Monthly allocations and manual revisions enforce public origins, distinct destinations and required test capacities.

## Catalog and capacity

Onboarders can add, edit, disable and remove consultations, laboratory tests, imaging and other facilities/equipment; each item has a PKR price and a declared daily capacity. Names are unique within a hospital, ignoring case and repeated spaces. Receptionists enter required catalog names, separated by commas; matching is exact after the same normalization, avoiding an unreviewed clinical substitution. All requested items must be active and have room at the destination.

Each held/confirmed/arrived referral consumes one unit of each required item on its service date; completed referrals retain the consumed unit. Cancellation releases test capacity. Approved, unconsumed monthly allocations also protect test units. Both the solver and manual plan revisions enforce the same limits. Confirmation rechecks catalog availability. Network OPD quota remains a separate constraint; test capacity cannot bypass it. Declared prices are displayed in the catalog; they do not silently become subsidy amounts or payment charges.

Green means more than 20% of declared network quota remains; amber means positive capacity at or below 20%; red means zero capacity. Stale reports and inactive hospitals are grey. Held, committed, completed and forfeited units all reduce remaining quota. These are reported network quotas, not measured total bed occupancy. Hospitals must update their dated quota and catalog when availability changes.

## Patient message demo

Reception intake captures an optional international-format WhatsApp number and explicit consent covering service names. A number cannot be stored without consent. Confirmation writes a message preview containing the patient reference, hospital name, address, service date, required services and reception instructions. Cancelling a confirmed referral writes a cancellation message; a newly confirmed destination writes a replacement confirmation. Proposals and tentative holds do not tell a patient to travel.

The outbox is written in the same database transaction as the referral transition and deduplicated by referral/event. It uses `PREVIEW_ONLY`; there is no transport call, sent status or delivery claim. Phone numbers are masked in the preview response and omitted from request audit snapshots and planning snapshots. Staff see only notifications for requests in their authorized workspace.

Open **Referral coordination → Open patient message demo** to launch `/patient-updates` in a separate tab. It inherits the signed-in staff session, refreshes every five seconds and shows WhatsApp-style chat bubbles. This is an authorized staff demonstration, not a patient login portal. Keep it open while confirming, cancelling and confirming a replacement referral to demonstrate the sequence. Consent-free requests produce no previews.

Live delivery is intentionally deferred. An API key alone does not complete integration: a transport adapter, WhatsApp Business sender/phone ID, access token, approved outbound templates, delivery webhooks and retry handling are still needed. Keep credentials on the backend. See [Meta's Cloud API documentation](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api).

## Verification and screenshots

The frontend uses larger body, form and map-label text. Desktop and 390px phone screenshots are saved in `docs/screenshots`; the README embeds the map, catalog and patient-message demo. Browser checks cover role-based login, private receiving-only controls, catalog visibility, a public-to-private confirmation/cancellation/reconfirmation sequence, and the separate message tab. Backend regression tests cover permissions, preference scoring before saturation, capacity colours, required-test capacity, consent and preview deduplication. Public deployment remains pending at the user's request.
