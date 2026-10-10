"use client";
import { useEffect, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  money,
  type Plan,
  type RevisionOptions,
} from "@/lib/api";

export function PlanRevision({
  plan,
  token,
  onSaved,
}: {
  plan: Plan;
  token: string;
  onSaved: (plan: Plan) => Promise<void>;
}) {
  const [options, setOptions] = useState<RevisionOptions | null>(null);
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [stale, setStale] = useState(false);
  async function load() {
    setBusy(true);
    try {
      const result = await api<RevisionOptions>(
        `plans/${plan.id}/revision-options`,
        token,
      );
      setOptions(result);
      setSelections(
        Object.fromEntries(
          result.current_assignments.map((a) => [a.request_id, a.resource_id]),
        ),
      );
      setStale(false);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void load();
  }, [plan.id]); // eslint-disable-line react-hooks/exhaustive-deps
  async function save(e: FormEvent) {
    e.preventDefault();
    if (!options) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<Plan>(`plans/${plan.id}/revise`, token, "POST", {
        version: options.version,
        reason,
        assignments: Object.entries(selections)
          .filter(([, id]) => id)
          .map(([request_id, resource_id]) => ({ request_id, resource_id })),
      });
      await onSaved(result);
    } catch (e) {
      setError((e as Error).message);
      if (
        e instanceof ApiError &&
        ["STALE_INPUT", "INVALID_TRANSITION"].includes(e.code)
      )
        setStale(true);
    } finally {
      setBusy(false);
    }
  }
  const requests = [
    ...new Set(options?.choices.map((c) => c.request_id) || []),
  ].sort();
  return (
    <form onSubmit={save}>
      <p>
        Revise draft selections for an operational reason. Omitted requests
        remain unresolved. The server validates the complete combination and
        derives all totals.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <button type="button" disabled={busy} onClick={() => void load()}>
        Reload current draft choices
      </button>
      {stale && (
        <p>
          Reload choices if another planner edited this draft. If operational
          inputs changed, close this editor and create a new snapshot and plan.
        </p>
      )}
      {options && (
        <>
          <p>
            Draft version {options.version} · Available budget PKR{" "}
            {money(options.remaining_budget)}
          </p>
          <div className="table-scroll revision-choices">
            <table>
              <thead>
                <tr>
                  <th>Request</th>
                  <th>Eligible resource</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((id) => (
                  <tr key={id}>
                    <td>{id}</td>
                    <td>
                      <select
                        aria-label={`Resource for ${id}`}
                        value={selections[id] || ""}
                        disabled={busy}
                        onChange={(e) =>
                          setSelections({ ...selections, [id]: e.target.value })
                        }
                      >
                        <option value="">Leave unresolved</option>
                        {options.choices
                          .filter((c) => c.request_id === id)
                          .map((c) => (
                            <option key={c.resource_id} value={c.resource_id}>
                              {c.facility_id} · {c.date} · Subsidy PKR{" "}
                              {money(c.subsidy)}
                              {c.funding_included ? " · funding included" : ""}
                            </option>
                          ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <details>
            <summary>Resource capacity and fixed cost</summary>
            {options.resources.map((r) => (
              <p key={r.id}>
                {r.id}: {r.units} units · Fixed cost PKR {money(r.cost)}
              </p>
            ))}
          </details>
          <label className="standalone-label">
            Reason for draft revision
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              minLength={3}
              maxLength={500}
            />
          </label>
          <button className="primary" disabled={busy || stale}>
            Save draft revision
          </button>
        </>
      )}
    </form>
  );
}
