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
  service_reviewed: boolean;
  date_from: string;
  date_to: string;
  status: string;
  reasons: string[];
  needs_funding: boolean;
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
  id: string;
  version: number;
  decision_source?: "SOLVER" | "HUMAN_REVISION";
  original_solver_result?: { coverage: number; cost: number; status: string };
  revisions?: {
    version: number;
    reason: string;
    actor: string;
    timestamp: string;
  }[];
  month: string;
  status: string;
  solver_status: string;
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
  status: string;
  model_version: string;
  candidates: {
    id: string;
    name: string;
    score: number;
    exact_alias: boolean;
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
  reviews: {
    id: string;
    input_text: string;
    decision: string;
    candidate_id: string;
    actor: string;
  }[];
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
