"use client";

import { useEffect, useState } from "react";
import type { State } from "@/lib/api";

type Step = { title: string; text: string; screen: string; button?: string; scope?: string; done?: boolean };

export function GuidedDemo({ state, screen, navigate }: {
  state: State; screen: string; navigate: (screen: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [journey, setJourney] = useState("route");
  const [requestId, setRequestId] = useState("A-01");
  const planner = state.user.role === "planner";
  const onboarder = state.user.role === "onboarder";
  const canSend = state.facilities.some(f => state.user.facility_ids.includes(f.id) && f.ownership === "Public" && f.participation === "ACTIVE");
  const key = `sehat-demo-${state.user.id}`;
  useEffect(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(key) || "null");
      if (saved) { setOpen(saved.open === true); setIndex(saved.index || 0); setJourney(saved.journey || "route"); setRequestId(saved.requestId || "A-01"); }
    } catch { /* A damaged local preference must not block the app. */ }
  }, [key]);
  function save(next: { open?: boolean; index?: number; journey?: string; requestId?: string }) {
    const value = { open, index, journey, requestId, ...next };
    setOpen(value.open); setIndex(value.index); setJourney(value.journey); setRequestId(value.requestId);
    try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { /* Tour remains usable without browser storage. */ }
  }
  const plan = state.plans.find(p => p.month === state.config.month && p.status === "APPROVED") || state.plans.find(p => p.month === state.config.month);
  const request = state.requests.find(r => r.id === requestId);
  const referral = [...state.referrals].reverse().find(r => r.request_id === requestId && !["CANCELLED", "EXPIRED", "REJECTED", "NO_SHOW"].includes(r.status));
  const row = `[data-demo-request="${CSS.escape(requestId)}"]`;
  const card = `[data-demo-referral="${CSS.escape(requestId)}"]`;
  let steps: Step[];
  if (planner) {
    steps = [
      { title: "Explore the hospital network", text: "Search PIMS, select a hospital and compare Capacity, Unmet demand and Funding. These are reported network figures, not hospital workload.", screen: "network", scope: ".pilot-map" },
      { title: "Understand the unmet demand", text: "Open the area breakdown. The worked example starts with 8 South affordability requests, 7 Central quota requests and 5 North requests without an eligible partner. Counts change as care is recorded.", screen: "intelligence" },
      { title: "Inspect or create the resource plan", text: plan ? `Open ${plan.id}: ${plan.status.toLowerCase()}, PKR ${plan.cost.toLocaleString("en-PK")}, ${plan.additional} projected additional services. Continue this plan; inspect available budget before creating another.` : "Click Create snapshot & optimize. Inspect the AI decision trace and cost breakdown before approving. An untouched demo projects 20 additional services for PKR 25,000.", screen: "planning", button: plan ? undefined : "Create snapshot & optimize", done: !!plan },
      { title: "Approve, then hand off activation", text: plan?.status === "APPROVED" ? `${plan.id} is already approved. Sign in as operator-p02 to activate QUOTA-7, then operator-p08 to activate MOBILE-5, using their Offers & activation walkthrough.` : "Select the draft, review its assumptions and click Approve plan. Approval commits funding; the receiving hospitals still need to activate offered resources.", screen: "planning", button: plan?.status === "APPROVED" ? undefined : "Approve plan", done: plan?.status === "APPROVED" },
      { title: "Compare the projection with recorded care", text: "Open Monthly outcomes. Keep projected, confirmed and completed totals separate. Return to the plan to download JSON/CSV summaries after the hospitals complete referrals.", screen: "outcomes" },
    ];
  } else if (onboarder) {
    steps = [
      { title: "Check your hospital setup", text: "Review hospital identity, eligible areas and dated network quota. Use the displayed service date. Keep worked-example quotas unchanged until the planning demonstration is finished.", screen: "network" },
      { title: "Add a service or test", text: "Add Complete blood count - E2E, category Laboratory, PKR 900 and daily capacity 30. Catalog capacity is separate from the primary-care network quota.", screen: "catalog", button: "Add service or test" },
      { title: "Verify persistence and visibility", text: "Reload, reopen Services & prices, then edit the test to PKR 1,200 and capacity 25. Sign in as planner in another tab and inspect this hospital's catalog.", screen: "catalog" },
      { title: "Finish the catalog demonstration", text: "Remove your E2E test after recording the result. Onboarding manages hospital setup and catalogs; reception handles patient referrals.", screen: "catalog" },
    ];
  } else if (journey === "intake" && canSend) {
    steps = [
      { title: "Ask AI to suggest the service", text: "Enter ‘a routine visit with a family physician’ in Service description, then Suggest service category. Expand How this suggestion was made to inspect the model and similarity evidence.", screen: "referrals", button: "Suggest service category" },
      { title: "Record the human review", text: "Accept or correct the primary-care suggestion explicitly. Human review recorded must appear before registration; a similarity score is not clinical confidence.", screen: "referrals" },
      { title: "Register a suitable request", text: "Use a unique E2E reference, your assigned public hospital, East zone and the displayed service date. Confirm non-emergency suitability. For the worked P03 example choose Kulsum (P04), not the originating hospital.", screen: "referrals", button: "Register request" },
      { title: "Continue with the referral walkthrough", text: "Choose Route / receive a request above, select your new reference, then follow proposal, reservation, confirmation and completion.", screen: "referrals" },
    ];
  } else if (journey === "activation") {
    steps = [
      { title: "Select the approved plan", text: plan ? `Open ${plan.id} in Offers & activation. Only resources offered by your assigned hospital can be activated here.` : "Ask the government representative to optimize and approve a plan first, then refresh this screen.", screen: "planning", done: plan?.status === "APPROVED" },
      { title: "Activate your hospital's resource", text: "PIMS (operator-p02) activates QUOTA-7. NORI (operator-p08) activates MOBILE-5. Click Confirm & activate offered resource for your pending action. Activated resources still require actual patient referrals.", screen: "planning", button: "Confirm & activate offered resource" },
      { title: "Route the previously unresolved demand", text: "Sign in as operator-p08 and choose B-01 in the routing walkthrough. Reprocess it with a reason, then find the activated PIMS quota. PIMS accepts and completes the incoming referral.", screen: "referrals" },
    ];
  } else {
    const owned = !!request && state.user.facility_ids.includes(request.source_facility_id);
    const source = request && state.facilities.find(f => f.id === request.source_facility_id);
    const legacy = owned && source?.ownership !== "Public";
    steps = [
      { title: `Locate ${request?.reference || requestId}`, text: !request ? "No matching request is visible for this account. In a fresh demo operator-p08 (NORI) originates A-01 and B-01. A-01's destination is Shifa (P01); Shifa receives it after NORI reserves it." : legacy ? "This is a legacy private-origin request. The updated policy permits only public hospitals to originate referrals. Continue an existing reserved referral if available; use a public-origin request for a new routing demonstration." : `Current request status: ${request.status.toLowerCase().replaceAll("_", " ")}. ${owned ? "Find its row in the request table below." : "You are the receiving hospital. Find its incoming referral card below; the public sending hospital selects the destination."}`, screen: "referrals", scope: referral ? card : row },
      { title: "Choose the destination and save a proposal", text: referral ? `A referral already exists (${referral.id}, ${referral.status.toLowerCase().replaceAll("_", " ")}). Continue that card rather than creating a duplicate.` : !owned || !canSend ? "Ask the originating public hospital to Find providers, choose the destination and Save referral proposal. Private reception accounts receive referrals rather than originate them." : "Click Find providers on this request, inspect Eligibility and ranking checks, choose a destination and Save referral proposal. A-01 goes to Shifa (P01) in the worked example. A proposal holds no quota or funding.", screen: "referrals", scope: referral ? card : row, button: !referral && owned && canSend ? "Find providers" : undefined, done: !!referral },
      { title: "Reserve the proposal", text: referral && referral.status !== "PROPOSED" ? "This referral is already reserved. Review the partner, patient and funding indicators on its card." : "The sending receptionist clicks Approve & reserve proposal on the saved card. This creates a temporary hold; the request row then hides Find providers while the referral is in progress.", screen: "referrals", scope: card, button: referral?.status === "PROPOSED" ? "Approve & reserve proposal" : undefined, done: !!referral && referral.status !== "PROPOSED" },
      { title: "Obtain the required confirmations", text: referral?.status === "COMPLETED" ? "This referral is already completed. Review its recorded outcome." : `Partner: ${referral?.partner_accepted ? "accepted" : "pending"}; patient: ${referral?.patient_agreed ? "agreed" : "pending"}; funding: ${referral?.funding_approved ? "authorized" : "pending"}. The receiving account accepts; staff records patient agreement. For A-01 the receiver is operator-p01. Government authorizes funding if it is still pending.`, screen: "referrals", scope: card, button: referral?.status === "AWAITING_CONFIRMATIONS" ? (!referral.partner_accepted && state.user.facility_ids.includes(referral.facility_id) ? "Accept referral" : !referral.patient_agreed ? "Record patient agreement" : undefined) : undefined, done: !!referral?.partner_accepted && !!referral?.patient_agreed && !!referral?.funding_approved },
      { title: "Record arrival and completion", text: referral?.status === "COMPLETED" || request?.status === "FULFILLED" ? "Care is recorded as completed. The active card may disappear; verify the fulfilled request and government outcomes." : "As the receiving hospital, Record arrival once confirmed, then Complete service. Refresh the sending and government tabs to see the shared result.", screen: "referrals", scope: card, button: referral?.status === "CONFIRMED" ? "Record arrival" : referral?.status === "ARRIVED" ? "Complete service" : undefined, done: referral?.status === "COMPLETED" || request?.status === "FULFILLED" },
    ];
  }
  const currentIndex = Math.min(index, steps.length - 1);
  const step = steps[currentIndex];
  useEffect(() => {
    if (!open || screen !== step.screen) return;
    const frame = requestAnimationFrame(() => {
      const scope = step.scope ? document.querySelector(step.scope) : document;
      if (!scope) return;
      const target = step.button
        ? Array.from(scope.querySelectorAll("button")).find(e => !e.closest(".guided-demo") && e.textContent?.trim() === step.button)
        : scope instanceof HTMLElement ? scope : document.querySelector(`[data-demo-nav="${step.screen}"]`);
      target?.classList.add("demo-highlight");
      target?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    return () => { cancelAnimationFrame(frame); document.querySelectorAll(".demo-highlight").forEach(e => e.classList.remove("demo-highlight")); };
  }, [open, screen, step.scope, step.button, step.screen, currentIndex, state]);
  if (!open) return <div className="demo-launch"><button onClick={() => save({ open: true })}>Start guided demo</button></div>;
  return <section className="guided-demo" aria-label="Guided demonstration">
    <div className="demo-tour-top"><strong>Guided demo · Step {currentIndex + 1} of {steps.length}</strong><button onClick={() => save({ open: false })}>Close guide</button></div>
    {!planner && !onboarder && <div className="demo-tour-selects">
      <label>Workflow <select value={journey} onChange={e => save({ journey: e.target.value, index: 0 })}><option value="route">Route / receive a request</option>{canSend && <option value="intake">AI-assisted intake</option>}<option value="activation">Offers & activation</option></select></label>
      {journey === "route" && <label>Request <select value={requestId} onChange={e => save({ requestId: e.target.value, index: 0 })}>{!state.requests.some(r => r.id === requestId) && <option value={requestId}>{requestId} (not visible for this account)</option>}{state.requests.map(r => <option key={r.id} value={r.id}>{r.reference} · {r.status.toLowerCase().replaceAll("_", " ")}</option>)}</select></label>}
    </div>}
    <h2>{step.title}{step.done && <span className="demo-step-recorded">Recorded</span>}</h2><p>{step.text}</p>
    <div className="demo-tour-controls"><button disabled={currentIndex === 0} onClick={() => save({ index: currentIndex - 1 })}>Back</button><button className="primary" onClick={() => navigate(step.screen)}>Show this step</button><button onClick={() => currentIndex === steps.length - 1 ? save({ open: false, index: 0 }) : save({ index: currentIndex + 1 })}>{currentIndex === steps.length - 1 ? "Finish guide" : "Next step"}</button></div>
    <small>Follow the highlighted control. Next step advances the guide; your actions and saved records determine workflow completion. You can close and resume this guide in this tab.</small>
  </section>;
}
