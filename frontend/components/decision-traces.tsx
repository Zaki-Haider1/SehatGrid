"use client";

import { useEffect, useState } from "react";
import {
  api,
  CareRequest,
  DemandSnapshot,
  Match,
  Plan,
  PlanDecision,
  RecommendationResult,
  Review,
  State,
  human,
  money,
} from "@/lib/api";

function TraceRows({
  rows,
}: {
  rows: [string, string | number | boolean | null | undefined][];
}) {
  return (
    <dl className="trace-rows">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>
            {value === true
              ? "Yes"
              : value === false
                ? "No"
                : (value ?? "Not provided")}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function reviewTarget(review: Review, state: State) {
  if (review.decision === "DECLINE") return "No canonical record selected";
  const record =
    state.services.find((service) => service.id === review.candidate_id) ||
    state.facilities.find((facility) => facility.id === review.candidate_id);
  return record?.name || review.candidate_id || "No canonical record selected";
}

export function MatchDecisionTrace({
  match,
  state,
  reviews,
}: {
  match: Match;
  state: State;
  reviews: Review[];
}) {
  const review = [...reviews]
    .reverse()
    .find((entry) => entry.match_id === match.id);
  const top = match.candidates[0];
  const supported = match.status === "NEEDS_REVIEW" && top;

  return (
    <details className="decision-trace">
      <summary>How this suggestion was made</summary>
      <TraceRows
        rows={[
          ["Original description", match.input_text],
          [
            supported
              ? "Suggested canonical record"
              : "Supported canonical record",
            supported ? top.name : "No supported match",
          ],
          [
            "Similarity score",
            top
              ? `${top.score.toFixed(3)} (similarity, not probability or clinical confidence)`
              : "Not available",
          ],
          [
            "Review status",
            review ? "Human decision recorded" : "Human review pending",
          ],
          [
            "Recorded decision",
            review
              ? `${review.decision}: ${reviewTarget(review, state)}`
              : "No human decision recorded",
          ],
        ]}
      />
      {match.status === "NO_SUPPORTED_MATCH" && (
        <p className="trace-note">
          The model found no candidate that meets the supported match rule.
          Leave this unreviewed or record an explicit decline; no match is
          approved automatically.
        </p>
      )}
      {match.ambiguous && (
        <p className="trace-note">
          The leading candidates are close in similarity, so the result is
          ambiguous and requires human review.
        </p>
      )}
      {review?.reason && (
        <p className="trace-note">Review reason: {review.reason}</p>
      )}
      <details className="trace-technical">
        <summary>Model and candidate details</summary>
        <TraceRows
          rows={[
            ["Model identifier / version", match.model_version],
            ["Normalized description", match.normalized_text],
            ["Backend score note", match.score_note],
          ]}
        />
        {match.candidates.map((candidate) => (
          <p key={candidate.id} className="trace-candidate">
            {candidate.name} · similarity {candidate.score.toFixed(3)} ·
            semantic {candidate.semantic.toFixed(3)}
          </p>
        ))}
      </details>
      {review && (
        <p className="trace-note">
          Recorded by {review.actor} ·{" "}
          {new Date(review.created_at).toLocaleString()}
        </p>
      )}
    </details>
  );
}

export function ReferralDecisionTrace({
  request,
  result,
  state,
}: {
  request: CareRequest;
  result: RecommendationResult | null;
  state: State;
}) {
  const service = state.services.find(
    (entry) => entry.id === request.service_id,
  );
  const review = state.reviews.find((entry) => entry.id === request.review_id);
  return (
    <details className="decision-trace">
      <summary>Eligibility and ranking checks</summary>
      <p>
        These are deterministic eligibility and ranking rules. They are not ML
        model decisions.
      </p>
      <TraceRows
        rows={[
          [
            "Reviewed service",
            `${request.service_reviewed ? "Reviewed" : "Not reviewed"} · ${service?.name || request.service_id || "No canonical service"}`,
          ],
          ["Original service description", request.original_text],
          [
            "Recorded human decision",
            review
              ? `${review.decision} · ${review.candidate_id ? service?.name || review.candidate_id : "No canonical record selected"}`
              : request.review_id
                ? "Review record is not available in this role scoped view"
                : "No matching review is recorded",
          ],
          ["Request zone", request.zone],
          [
            "Requested service dates",
            `${request.date_from} to ${request.date_to}`,
          ],
          ["Funding need declared", request.needs_funding],
        ]}
      />
      {result?.candidates.length ? (
        result.candidates.map((candidate) => {
          const checks = candidate.eligibility;
          return (
            <section className="trace-destination" key={candidate.capacity_id}>
              <strong>
                {candidate.name} · {checks.service_date}
              </strong>
              <TraceRows
                rows={[
                  [
                    "Service review",
                    `${checks.reviewed_service_id} · ${checks.service_reviewed ? "reviewed" : "not reviewed"}`,
                  ],
                  [
                    "Declared zone eligibility",
                    `${checks.request_zone} is ${checks.zone_eligible ? "included" : "not included"} · ${checks.declared_eligible_zones.join(", ") || "no zones declared"}`,
                  ],
                  [
                    "Date in requested window",
                    `${checks.service_date} · ${checks.requested_date_from} to ${checks.requested_date_to} · ${checks.within_requested_dates ? "yes" : "no"}`,
                  ],
                  [
                    "Quota freshness",
                    `${checks.quota_fresh ? "Fresh" : "Stale or unknown"} · updated ${checks.quota_updated_at}`,
                  ],
                  ["Available capacity returned", checks.available_capacity],
                  [
                    "Funding check",
                    `${checks.request_needs_funding ? "Funding need declared" : "No funding need declared"} · ${checks.facility_subsidy_required ? "facility subsidy applies" : "facility does not require a subsidy"} · ${checks.funding_eligible ? "operationally eligible" : "not eligible"} · ${checks.funding_included ? "package funded" : "PKR " + money(checks.funding_amount)}${checks.funding_authorization_required ? " · authorization required" : ""}`,
                  ],
                  ["Backend explanation", candidate.explanation],
                ]}
              />
            </section>
          );
        })
      ) : result ? (
        <div className="trace-note">
          <strong>No destination was returned.</strong>
          <p>Unresolved reasons returned by the backend:</p>
          {result.reasons.length ? (
            <ul>
              {result.reasons.map((reason) => (
                <li key={reason}>{human(reason)}</li>
              ))}
            </ul>
          ) : (
            <p>No unresolved reason code was returned.</p>
          )}
        </div>
      ) : (
        <p className="trace-note">
          Refresh recommendations to see the backend checks and any unresolved
          reasons.
        </p>
      )}
      {result?.ranking_policy_version && (
        <TraceRows
          rows={[
            ["Applied ranking policy", result.ranking_policy_version],
            [
              "Applied criteria, in order",
              result.ranking_criteria?.map(human).join(" → ") ||
                "Criteria not returned",
            ],
          ]}
        />
      )}
    </details>
  );
}

function DecisionTotals({
  decision,
  label,
}: {
  decision: PlanDecision;
  label: string;
}) {
  return (
    <section className="trace-destination">
      <strong>{label}</strong>
      <TraceRows
        rows={[
          [
            "Projected assignments",
            decision.projected ??
              decision.coverage ??
              decision.assignments.length,
          ],
          ["Baseline feasible units", decision.baseline],
          [
            "Incremental cost",
            `PKR ${money(decision.cost)} · synthetic demo cost`,
          ],
          [
            "Subsidies",
            `${decision.assignments.filter((assignment) => assignment.subsidy > 0).length} · PKR ${money(decision.subsidy_cost)}`,
          ],
          [
            "Purchased quota / mobile resources",
            decision.actions
              .map(
                (action) =>
                  `${action.offer_id} (${human(action.kind)}): PKR ${money(action.cost)}`,
              )
              .join(" · ") || "None selected",
          ],
          ["Unresolved remainder", decision.unresolved_remaining],
        ]}
      />
    </section>
  );
}

export function AllocationDecisionTrace({
  plan,
  token,
}: {
  plan: Plan;
  token: string;
}) {
  const [snapshot, setSnapshot] = useState<DemandSnapshot | null>(null);
  const [snapshotError, setSnapshotError] = useState("");
  useEffect(() => {
    let active = true;
    setSnapshot(null);
    setSnapshotError("");
    api<DemandSnapshot>(`intelligence/snapshots/${plan.snapshot_id}`, token)
      .then((value) => {
        if (active) setSnapshot(value);
      })
      .catch((error: unknown) => {
        if (active)
          setSnapshotError(
            error instanceof Error
              ? error.message
              : "Snapshot could not be loaded",
          );
      });
    return () => {
      active = false;
    };
  }, [plan.id, plan.snapshot_id, token]);

  const current: PlanDecision = {
    cost: plan.cost,
    subsidy_cost: plan.subsidy_cost,
    projected: plan.projected,
    baseline: plan.baseline,
    additional: plan.additional,
    unresolved_remaining: plan.unresolved_remaining,
    assignments: plan.assignments,
    actions: plan.actions,
  };
  const original = plan.original_solver_result;

  return (
    <details className="decision-trace">
      <summary>How this plan was calculated</summary>
      <p>
        Projected accommodation is a plan estimate. It does not confirm that a
        service was delivered.
      </p>
      <TraceRows
        rows={[
          ["Demand snapshot", plan.snapshot_id],
          ["Input hash", plan.input_hash],
          [
            "Decision source",
            plan.decision_source === "HUMAN_REVISION"
              ? "Human revision"
              : plan.decision_source === "SOLVER"
                ? "Solver result"
                : "Not provided",
          ],
          [
            "Current persisted totals",
            `${plan.projected} projected · ${plan.additional} additional · ${plan.unresolved_remaining} unresolved · PKR ${money(plan.cost)}`,
          ],
          ["Baseline", plan.baseline],
          [
            "Current plan budget requirement",
            `PKR ${money(plan.cost)} · synthetic demo cost`,
          ],
        ]}
      />
      {snapshot ? (
        <>
          <TraceRows
            rows={[
              ["Snapshot timestamp", snapshot.timestamp],
              ["Dataset / input version", snapshot.dataset_version],
              ["Operational policy version", snapshot.policy_version],
              ["Budget input version", plan.budget_version],
              [
                "Eligible unresolved demand considered",
                snapshot.requests.length,
              ],
              [
                "Excluded demand",
                Object.entries(snapshot.excluded)
                  .map(([reason, count]) => `${human(reason)}: ${count}`)
                  .join(" · ") || "None recorded",
              ],
              [
                "Available budget at snapshot",
                snapshot.summary.budget
                  ? `PKR ${money(snapshot.summary.budget.remaining)} of PKR ${money(snapshot.summary.budget.authorized)}`
                  : "No budget record in snapshot",
              ],
              [
                "Capacity freshness rule",
                snapshot.operational_rules.freshness_minutes == null
                  ? "Not provided"
                  : `${snapshot.operational_rules.freshness_minutes} minutes`,
              ],
            ]}
          />
          {!snapshot.immutable && (
            <p className="trace-note">
              The API did not mark this snapshot immutable.
            </p>
          )}
        </>
      ) : (
        <p className="trace-note">
          {snapshotError || "Loading the persisted demand snapshot…"}
        </p>
      )}
      {original && (
        <DecisionTotals
          decision={{
            ...original,
            assignments: original.assignments || [],
            actions: original.actions || [],
          }}
          label={`Original solver result · ${human(original.status || plan.solver_status)} · ${plan.solver}`}
        />
      )}
      {!original && (
        <p className="trace-note">
          This persisted plan does not include a separate original solver
          result.
        </p>
      )}
      <DecisionTotals decision={current} label="Current persisted allocation" />
      {(plan.revisions?.length || 0) > 0 ? (
        <section className="trace-destination">
          <strong>Recorded human revisions</strong>
          {plan.revisions?.map((revision) => (
            <div className="trace-revision" key={revision.version}>
              <p>
                Revision {revision.version} · {revision.actor} ·{" "}
                {new Date(revision.timestamp).toLocaleString()}
              </p>
              <p>Reason: {revision.reason}</p>
              <p>
                After revision:{" "}
                {revision.after.projected ?? revision.after.assignments.length}{" "}
                projected · PKR {money(revision.after.cost)} ·{" "}
                {revision.after.unresolved_remaining} unresolved
              </p>
            </div>
          ))}
        </section>
      ) : (
        <p className="trace-note">No human plan revision is recorded.</p>
      )}
      {plan.assumptions.map((assumption) => (
        <p className="trace-note" key={assumption}>
          {assumption}
        </p>
      ))}
    </details>
  );
}
