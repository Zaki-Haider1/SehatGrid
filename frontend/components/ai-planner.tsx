"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
type Proposal = { title: string; budget_limit_pkr: number | null; excluded_offer_ids: string[]; allow_subsidies: boolean; rationale: string; clarification: string | null };
type Result = { snapshot_id?: string; proposal: Proposal; evidence: { eligible_requests: number; remaining_budget_pkr: number; bottlenecks: {zone: string; count: number; reasons: Record<string, number>}[] }; checked?: {status: string; projected_services: number; cost_pkr: number; unresolved_remaining: number; offer_ids: string[]; destinations: {facility_id: string; offer_id: string | null; projected_services: number; subsidy_cost_pkr: number}[]}; comparison?: {projected_services: number; cost_pkr: number; services_difference: number; cost_difference_pkr: number} };
const defaultGoal = "Help the most blocked requests within the remaining budget.";
const names: Record<string, string> = {P01: "Shifa", P02: "PIMS", P03: "Polyclinic", P04: "Kulsum", P05: "Maroof", P06: "Ali Medical", P07: "Capital Hospital", P08: "NORI", "site:MOBILE-5": "NORI mobile site"};
const reasonNames: Record<string, string> = {CAPACITY_EXHAUSTED: "quota exhausted", FUNDING_UNAVAILABLE: "funding unavailable", AFFORDABILITY: "affordability", NO_ELIGIBLE_PARTNER: "no eligible partner", CAPACITY_UNKNOWN_OR_STALE: "capacity needs verification"};
const money = (n: number) => n.toLocaleString("en-PK");
export function AIPlanner({ token, month, revision, onDraft }: { token: string; month: string; revision: string; onDraft: (snapshotId: string) => Promise<void> }) {
  const [expanded, setExpanded] = useState(false);
  const [question, setQuestion] = useState(defaultGoal), [result, setResult] = useState<Result | null>(null), [busy, setBusy] = useState(false), [creating, setCreating] = useState(false), [error, setError] = useState(""), [generatedGoal, setGeneratedGoal] = useState("");
  const sequence = useRef(0);
  async function propose(goal = question) {
    const id = ++sequence.current; setBusy(true); setError(""); setResult(null);
    try { const response = await api<Result>("ai/planning-advice", token, "POST", { month, question: goal }); if (id === sequence.current) { setResult(response); setGeneratedGoal(goal); } }
    catch (e) { if (id === sequence.current) setError(e instanceof Error ? e.message : "Could not prepare an AI proposal. You can use the standard planner below."); }
    finally { if (id === sequence.current) setBusy(false); }
  }
  useEffect(() => { if (expanded) void propose(); return () => { sequence.current++; }; }, [month, revision, expanded]); // eslint-disable-line react-hooks/exhaustive-deps
  async function createDraft() {
    if (!result?.snapshot_id) return;
    setCreating(true); setError("");
    try { await onDraft(result.snapshot_id); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not create the draft. Regenerate the proposal and retry."); }
    finally { setCreating(false); }
  }
  const checked = result?.checked;
  return <section className="ai-planner ai-planner-compact">
    <div className="ai-allocation-header"><div><span className="eyebrow">AI-ASSISTED ALLOCATION</span><h3>Resolve blocked demand.</h3><p>Propose resources, compare the trade-off, create a checked draft.</p></div><button type="button" className="ai-expand-button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? "Collapse" : "Plan with AI →"}</button></div>
    {expanded && <div className="ai-allocation-body">
    {result && <div className="ai-bottlenecks">{result.evidence.bottlenecks.filter(z => z.count > 0).map(z => <div key={z.zone}><strong>{z.count} · {z.zone}</strong><small>{Object.entries(z.reasons).map(([r, n]) => `${n} ${reasonNames[r] || r.toLowerCase().replaceAll("_", " ")}`).join(" · ")}</small></div>)}</div>}
    <label>Your allocation goal<textarea value={question} onChange={e => setQuestion(e.target.value)} maxLength={1500} disabled={creating} /></label>
    <div className="ai-goal-presets">{[["Most patients", defaultGoal], ["PKR 15,000 limit", "Help the most blocked requests with a spending cap of PKR 15,000."], ["No mobile resource", "Help the most blocked requests, but exclude mobile clinic offers; use eligible partner quota and subsidies."]].map(([label, goal]) => <button key={label} type="button" disabled={busy || creating} onClick={() => { setQuestion(goal); void propose(goal); }}>{label}</button>)}</div>
    <button className="primary" disabled={busy || creating || !question.trim()} onClick={() => void propose()}>{busy ? "Proposing and checking your plan…" : "Propose allocation"}</button>
    {error && <p role="alert" className="ai-plan-error">{error} The standard planner is available below.</p>}
    {result?.proposal.clarification && <p role="status" className="ai-plan-error"><strong>One detail needed:</strong> {result.proposal.clarification} Update your goal above and propose again.</p>}
    {checked && result && <div className="ai-checked-proposal" aria-live="polite">
      <div className="ai-proposal-heading"><h4>{result.proposal.title}</h4><span className="ai-check-badge">{checked.status === "OPTIMAL" ? "Checked · optimal" : "Checked · feasible"}</span></div>
      <details className="ai-proposal-reason"><summary>Why AI proposed this strategy</summary><p>{result.proposal.rationale}</p></details>
      <div className="ai-scenario-constraints"><span>Spending cap: PKR {money(result.proposal.budget_limit_pkr ?? result.evidence.remaining_budget_pkr)}</span><span>{result.proposal.allow_subsidies ? "Subsidies allowed" : "No subsidies"}</span>{result.proposal.excluded_offer_ids.map(id => <span key={id}>Exclude {id}</span>)}</div>
      <div className="ai-allocation-stats"><strong>{checked.projected_services} requests can be accommodated</strong><strong>PKR {money(checked.cost_pkr)} proposed cost</strong><strong>{checked.unresolved_remaining} eligible requests remain</strong></div>
      <div className="ai-interventions">{checked.destinations.map((d, i) => <div key={i}><div><strong>{names[d.facility_id] || d.facility_id}</strong><small>{d.offer_id ? `${d.offer_id} · activate after approval` : d.subsidy_cost_pkr ? `Subsidy support · PKR ${money(d.subsidy_cost_pkr)}` : "Use existing eligible quota"}</small></div><b>{d.projected_services} requests</b></div>)}</div>
      {result.comparison && <p className="ai-comparison">With all available resources and the full remaining budget: <strong>{result.comparison.projected_services} requests / PKR {money(result.comparison.cost_pkr)}</strong>. This proposal accommodates {Math.abs(result.comparison.services_difference)} {result.comparison.services_difference < 0 ? "fewer" : "more"} requests and {result.comparison.cost_difference_pkr <= 0 ? "costs PKR " + money(Math.abs(result.comparison.cost_difference_pkr)) + " less" : "costs PKR " + money(result.comparison.cost_difference_pkr) + " more"}.</p>}
      <button className="primary" disabled={busy || creating || question !== generatedGoal || checked.projected_services === 0} onClick={() => void createDraft()}>{creating ? "Creating checked draft…" : "Create draft from this proposal →"}</button>
      {question !== generatedGoal && <small>Your goal changed. Propose again before creating a draft.</small>}
    </div>}
    <small>Projected care, not delivered care. Creating a draft reserves nothing. Review and approve it below; hospitals then activate resources and coordinate referrals. Unknown or stale capacity still needs staff verification.</small></div>}
  </section>;
}
