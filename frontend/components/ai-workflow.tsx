"use client";
import { useEffect, useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import { api } from "@/lib/api";
type Advice = {summary: string; next_steps: string[]; cautions: string[]};
export function AIWorkflow({ token, requestId, facilityId, revision = "" }: { token: string; requestId?: string; facilityId?: string; revision?: string }) {
  const [advice, setAdvice] = useState<Advice | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const sequence = useRef(0);
  useEffect(() => { sequence.current++; setAdvice(null); setError(""); setBusy(false); }, [requestId, facilityId, revision]);
  async function suggest() {
    const id = ++sequence.current;setBusy(true);setError("");
    try { const result = await api<{advice: Advice}>("ai/workflow-help",token,"POST",{request_id:requestId,facility_id:facilityId});if(id===sequence.current)setAdvice(result.advice); }
    catch(e) { if(id===sequence.current)setError(e instanceof Error ? e.message : "Guidance unavailable. Continue using the normal controls."); }
    finally { if(id===sequence.current)setBusy(false); }
  }
  return <aside className="ai-workflow" aria-label={facilityId ? "AI hospital setup review" : "AI reception guidance"}>
    <div className="ai-workflow-header"><Sparkles size={16} /><div><strong>{facilityId ? "AI setup review" : "AI next step"}</strong><small>{facilityId ? "Check this hospital's setup and catalog" : requestId ? `Guidance for ${requestId}` : "Help with your assigned requests"}</small></div><button type="button" disabled={busy} onClick={() => void suggest()}>{busy ? "Checking…" : advice ? "Refresh" : facilityId ? "Review setup" : "Suggest"}</button></div>
    {error && <p role="status">{error}</p>}
    {advice && <div className="ai-workflow-result" aria-live="polite"><p>{advice.summary}</p><ol>{advice.next_steps.slice(0,3).map((step,i)=><li key={i}>{step}</li>)}</ol>{advice.cautions.length>0 && <details><summary>Things to check</summary>{advice.cautions.slice(0,2).map((c,i)=><p key={i}>{c}</p>)}</details>}<small>Qwen 3.8 27B · Staff reviews and performs each action.</small></div>}
  </aside>;
}
