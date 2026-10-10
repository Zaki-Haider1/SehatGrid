"use client";
import { ArrowUpRight, CalendarDays, CheckCircle2, Wallet } from "lucide-react";
import { money, human, type State } from "@/lib/api";
export function MonthlyOutcomes({
  state,
  navigate,
}: {
  state: State;
  navigate: (screen: string) => void;
}) {
  const summary = state.summary!,
    plans = state.plans.filter((p) => p.month === summary.month),
    approved = plans.filter((p) =>
      ["APPROVED", "ACTIVE", "CLOSED"].includes(p.status),
    ),
    p = approved.at(-1),
    budget = summary.budget;
  return (
    <div className="monthly-outcomes">
      <section className="card">
        <div className="card-title">
          <div>
            <span className="eyebrow">PLAN & DELIVERY · {summary.month}</span>
            <h2>Did the plan turn into care?</h2>
          </div>
          <CalendarDays size={21} color="#8fa4d7" />
        </div>
        <p>
          Compare the approved projection with services confirmed and completed
          after resource activation. Use the planning month above to review an
          earlier period.
        </p>
        {p ? (
          <>
            <div className="outcome-bars">
              {[
                [
                  "Planned additional services",
                  summary.projected_additional,
                  "#8aa5f0",
                ],
                [
                  "Confirmed after activation",
                  summary.post_activation_confirmed,
                  "#8d9ab8",
                ],
                [
                  "Completed after activation",
                  summary.post_activation_completed,
                  "#e8a0a6",
                ],
              ].map(([label, value, color]) => (
                <div key={String(label)}>
                  <span>{label}</span>
                  <div>
                    <i
                      style={{
                        width: `${Math.min(100, (Number(value) / Math.max(summary.projected_additional, summary.post_activation_confirmed, summary.post_activation_completed, 1)) * 100)}%`,
                        background: String(color),
                      }}
                    />
                  </div>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
            <p className="outcome-caption">
              {summary.projected_additional === 0
                ? "This plan has no additional service projection."
                : `${Math.round((summary.post_activation_completed / summary.projected_additional) * 100)}% of the additional projection has a recorded completion.`}{" "}
              Confirmed services can still await attendance or completion.
            </p>
            <button onClick={() => navigate("planning")}>
              Review plan and resource actions
              <ArrowUpRight size={14} />
            </button>
          </>
        ) : (
          <div className="catalog-empty">
            <CheckCircle2 size={28} />
            <h3>No approved plan recorded for this month.</h3>
            <p>
              {summary.registered
                ? "Operational counts above show the recorded activity. Create a plan to compare projected and delivered care."
                : "There is no recorded request activity in this period yet."}
            </p>
            <button onClick={() => navigate("planning")}>
              Open monthly planner
              <ArrowUpRight size={14} />
            </button>
          </div>
        )}
      </section>
      <div className="two-col">
        <section className="card">
          <div className="card-title">
            <h2>Budget accountability</h2>
            <Wallet size={18} color="#8fa4d7" />
          </div>
          <dl className="outcome-facts">
            {[
              ["Authorized budget", budget?.authorized || 0],
              ["Held", budget?.HELD || 0],
              ["Committed", budget?.COMMITTED || 0],
              ["Settled expenditure", budget?.SETTLED || 0],
              ["Remaining", budget?.remaining || 0],
            ].map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>PKR {money(Number(value))}</dd>
              </div>
            ))}
          </dl>
          {!budget && <p>No budget authorized for this month.</p>}
        </section>
        <section className="card">
          <div className="card-title">
            <h2>Plans in this period</h2>
            <span className="count">{plans.length}</span>
          </div>
          {plans.length ? (
            plans.map((p) => (
              <div className="period-plan" key={p.id}>
                <div>
                  <strong>{p.id}</strong>
                  <span>
                    {p.additional} additional services · PKR {money(p.cost)}
                  </span>
                </div>
                <span className={`badge ${p.status.toLowerCase()}`}>
                  {human(p.status)}
                </span>
              </div>
            ))
          ) : (
            <p className="empty">No saved plans in this month.</p>
          )}
          <p className="subtle">
            Human revisions and decision reasons are available in the monthly
            planner and exports.
          </p>
        </section>
      </div>
    </div>
  );
}
