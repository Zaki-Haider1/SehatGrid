export const API = (
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  ""
).replace(/\/$/, "");
export type User = {
  id: string;
  name: string;
  role: "operator" | "planner" | "onboarder";
  facility_ids: string[];
};
export type Capacity = {
  id: string;
  facility_id: string;
  date: string;
  quota: number;
  held: number;
  committed: number;
  completed: number;
  forfeited: number;
  available: number | null;
  status: string;
  freshness: string;
  updated_at: string;
  version: number;
};
export type Facility = {
  routing_points?: number;
  routing_metrics?: {
    referrals: number;
    completed: number;
    completion_rate: number | null;
  };
  id: string;
  name: string;
  ownership: string;
  address: string;
  zone: string;
  latitude: number;
  longitude: number;
  participation: string;
  version: number;
  eligible_zones: string[];
  service_reviewed: boolean;
  subsidy_required: boolean;
  capacities: Capacity[];
  catalog?: CatalogItem[];
  directory_context?: {
    name: string;
    label: string;
    profile: {
      coordinate_source: string;
      coordinate_note: string;
      website?: string;
      directory_sources: { title: string; url: string }[];
    };
  };
};
export type CatalogItem = {
  id: string;
  name: string;
  category: "Consultation" | "Laboratory" | "Imaging" | "Other";
  price: number;
  daily_capacity: number;
  active: boolean;
};
export type CareRequest = {
  id: string;
  reference: string;
  source_facility_id: string;
  zone: string;
  original_text: string;
  service_id: string | null;
  service_reviewed: boolean;
  review_id?: string | null;
  date_from: string;
  date_to: string;
  status: string;
  reasons: string[];
  needs_funding: boolean;
  funding_eligible: boolean;
};
export type Referral = {
  id: string;
  request_id: string;
  facility_id: string;
  status: string;
  date: string;
  subsidy: number;
  patient_agreed: boolean;
  partner_accepted: boolean;
  funding_approved: boolean;
  expires_at?: string;
  reason?: string;
};
export type Budget = {
  month: string;
  authorized: number;
  version: number;
  HELD: number;
  COMMITTED: number;
  SETTLED: number;
  RELEASED: number;
  remaining: number;
};
export type Offer = {
  id: string;
  kind: string;
  facility_id: string;
  date: string;
  units: number;
  cost: number;
  status: string;
  site?: string;
};
export type Plan = {
  ai_scenario?: { goal: string; budget_limit_pkr: number; excluded_offer_ids: string[]; allow_subsidies: boolean } | null;
  id: string;
  snapshot_id: string;
  month: string;
  status: string;
  version: number;
  input_hash: string;
  budget_version: number;
  solver: string;
  solver_status: string;
  decision_source?: "SOLVER" | "HUMAN_REVISION";
  cost: number;
  subsidy_cost: number;
  baseline: number;
  projected: number;
  additional: number;
  unresolved_remaining: number;
  assignments: {
    request_id: string;
    facility_id: string;
    date: string;
    subsidy: number;
    offer_id: string | null;
  }[];
  actions: {
    id: string;
    offer_id: string;
    kind: string;
    cost: number;
    status: string;
  }[];
  assumptions: string[];
  excluded: Record<string, number>;
  runtime_seconds: number;
  original_solver_result?: PlanDecision | null;
  revisions?: {
    version: number;
    actor: string;
    timestamp: string;
    reason: string;
    before: PlanDecision;
    after: PlanDecision;
  }[];
};
export type PlanDecision = {
  status?: string;
  coverage?: number;
  cost: number;
  subsidy_cost: number;
  projected?: number;
  baseline?: number;
  additional: number;
  unresolved_remaining: number;
  assignments: Plan["assignments"];
  actions: Plan["actions"];
};
export type DemandSnapshot = {
  id: string;
  month: string;
  timestamp: string;
  input_hash: string;
  dataset_version: string;
  policy_version: string;
  origin_type: string;
  immutable: boolean;
  requests: unknown[];
  excluded: Record<string, number>;
  summary: { budget: Budget | null };
  operational_rules: Record<string, string | number>;
};
export type RevisionOptions = {
  contract_version: "plan-revision-v1";
  version: number;
  current_assignments: { request_id: string; resource_id: string }[];
  remaining_budget: number;
  resources: {
    id: string;
    units: number;
    cost: number;
    facility_id: string;
    date: string;
  }[];
  choices: {
    request_id: string;
    resource_id: string;
    facility_id: string;
    date: string;
    subsidy: number;
    funding_included: boolean;
  }[];
};
export type Match = {
  id: string;
  kind: "service" | "facility";
  input_text: string;
  normalized_text: string;
  status: string;
  ambiguous: boolean;
  threshold: number;
  score_note: string;
  model_version: string;
  candidates: {
    id: string;
    name: string;
    score: number;
    semantic: number;
    exact_alias: boolean;
    locality_match: boolean;
    type_match: boolean;
  }[];
};
export type Recommendation = {
  routing_score: number;
  routing_points: number;
  ranking_policy_version: string;
  facility_id: string;
  name: string;
  capacity_id: string;
  date: string;
  available: number;
  subsidy: number;
  capacity_version: number;
  facility_version: number;
  explanation: string;
  same_zone: boolean;
  package_funded: boolean;
  funding_authorization_required: boolean;
  eligibility: {
    service_reviewed: boolean;
    reviewed_service_id: string;
    request_zone: string;
    declared_eligible_zones: string[];
    zone_eligible: boolean;
    service_date: string;
    requested_date_from: string;
    requested_date_to: string;
    within_requested_dates: boolean;
    quota_fresh: boolean;
    quota_updated_at: string;
    available_capacity: number;
    request_needs_funding: boolean;
    facility_subsidy_required: boolean;
    funding_eligible: boolean;
    funding_included: boolean;
    funding_authorization_required: boolean;
    funding_amount: number;
  };
};
export type RecommendationResult = {
  candidates: Recommendation[];
  reasons: string[];
  ranking_policy_version?: string;
  ranking_criteria?: string[];
  policy_version?: string;
};
export type Review = {
  id: string;
  match_id: string;
  kind: "service" | "facility";
  input_text: string;
  candidates: Match["candidates"];
  model_version: string;
  decision: "ACCEPT" | "CORRECT" | "DECLINE";
  candidate_id: string | null;
  reason: string;
  actor: string;
  created_at: string;
};
export type RankingPolicy = {
  criteria: ("same_zone" | "subsidy" | "available")[];
  version: number;
  policy_version: string;
};
export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public status: number,
  ) {
    super(message);
  }
}
export type Summary = {
  month: string;
  unresolved: number;
  registered: number;
  confirmed: number;
  arrived: number;
  completed: number;
  projected_additional: number;
  post_activation_confirmed: number;
  post_activation_completed: number;
  zones: { zone: string; count: number; reasons: Record<string, number> }[];
  budget: Budget | null;
};
export type State = {
  notifications?: {
    id: string;
    request_id: string;
    recipient: string;
    status: string;
    message: string;
    created_at: string;
  }[];
  user: User;
  config: {
    today: string;
    service_date: string;
    month: string;
    scope_version: string;
    dataset_version: string;
    freshness_minutes: number;
    hold_minutes: number;
    cutoff: string;
    model: string;
    zones: { id: string; name: string; latitude: number; longitude: number }[];
  };
  facilities: Facility[];
  services: { id: string; name: string }[];
  requests: CareRequest[];
  referrals: Referral[];
  summary: Summary | null;
  budgets: Budget[];
  ledger: { id: string; amount: number; state: string; reference: string }[];
  plans: Plan[];
  offers: Offer[];
  reviews: Review[];
  audit: {
    id: string;
    action: string;
    actor: string;
    timestamp: string;
    object_id: string;
    reason?: string;
  }[];
  subsidy_rule: { amount: number; month: string; version: number } | null;
};
export async function api<T>(
  path: string,
  token: string,
  method = "GET",
  body?: unknown,
  key?: string,
): Promise<T> {
  const response = await fetch(`${API}/api/v1/${path}`, {
    method,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(method !== "GET"
        ? { "Idempotency-Key": key || crypto.randomUUID() }
        : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(60000),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      typeof data.detail === "string"
        ? data.detail
        : data.detail?.message || "The server could not complete this action",
      data.detail?.code || "API_ERROR",
      response.status,
    );
  }
  return response.json();
}
export function money(value: number) {
  return new Intl.NumberFormat("en-PK", { maximumFractionDigits: 0 }).format(
    value,
  );
}
export function hospitalName(facility: Facility) {
  return /^Demo\b.*\bProvider P\d+$/.test(facility.name)
    ? facility.directory_context?.name || facility.name
    : facility.name;
}
export function hospitalShortName(facility: Facility) {
  const name = hospitalName(facility);
  const labels: Record<string, string> = {
    "Shifa International Hospital": "Shifa",
    "Pakistan Institute of Medical Sciences (PIMS)": "PIMS",
    "Federal Government Polyclinic": "Polyclinic",
    "Kulsum International Hospital": "Kulsum",
    "Maroof International Hospital": "Maroof",
    "Ali Medical Centre": "Ali Medical",
    "Capital Hospital (CDA)": "CDA",
    "NORI Atomic Energy Cancer Hospital": "NORI",
  };
  return labels[name] || name;
}
export function human(value: string) {
  return value.replaceAll("_", " ").toLowerCase();
}
