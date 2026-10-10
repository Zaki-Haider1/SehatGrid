"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
type Result = { model: string; snapshot_id: string; advice: { summary: string; next_steps: string[]; cautions: string[] }; evidence: { cost_pkr: number; projected_coverage: number; remaining_budget_pkr: number; solver_status: string } };
export function AIPlanner({ token, month, revision }: { token: string; month: string; revision: string }) {
  const [question, setQuestion] = useState("Where should we allocate resources next, and what should each hospital do?");
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  async function refresh() {
    const id = ++sequence.current;
    setBusy(true); setError(""); setResult(null);
    try { const response = await api<Result>("ai/planning-advice", token, "POST", { month, question }); if (id === sequence.current) setResult(response); }
    catch (e) { if (id === sequence.current) setError(e instanceof Error ? e.message : "AI advice unavailable. You can still create a resource plan below."); }
    finally { if (id === sequence.current) setBusy(false); }
  }
  useEffect(() => { void refresh(); return () => { sequence.current++; }; }, [month, revision]); // eslint-disable-line react-hooks/exhaustive-deps
  return <section className="ai-planner">
    <span className="eyebrow">QWEN 3.8 27B · RESOURCE ADVISOR</span><h3>What should we allocate next?</h3>
    <p>AI explains a feasible allocation checked against today's recorded demand, dated capacity and remaining budget. Suggestions update when this workspace refreshes after demand or plan changes.</p>
    <label>Ask about this allocation<textarea value={question} onChange={e => setQuestion(e.target.value)} maxLength={1500} /></label>
    <button className="primary" disabled={busy || !question.trim()} onClick={() => void refresh()}>{busy ? "Checking resources and preparing advice…" : "Refresh AI suggestions"}</button>
    {error && <p role="status">{error} Use Create snapshot & optimize below to continue.</p>}
    {result && <div aria-live="polite"><div className="ai-allocation-stats"><strong>{result.evidence.projected_coverage} projected services</strong><strong>PKR {result.evidence.cost_pkr.toLocaleString()} proposed cost</strong><span>{result.evidence.solver_status} · {result.snapshot_id}</span></div><p>{result.advice.summary}</p><h4>Recommended next actions</h4><ol>{result.advice.next_steps.map((s, i) => <li key={i}>{s}</li>)}</ol>{result.advice.cautions.length > 0 && <details><summary>Assumptions and cautions</summary><ul>{result.advice.cautions.map((s, i) => <li key={i}>{s}</li>)}</ul></details>}</div>}
    <small>AI advice is a preview. Create and review a draft below, then approve it explicitly. No slots or money are reserved here. Questions explain the existing allocation; they do not change solver constraints.</small>
  </section>;
}
