export type Service = { id: number; name: string; unit_cost: number };
export type Capacity = {
  service_id: number;
  service_name: string;
  total: number;
  available: number;
  reserved: number;
  consumed: number;
};
export type Facility = {
  id: number;
  name: string;
  kind: string;
  zone: string;
  latitude: number;
  longitude: number;
  capacities: Capacity[];
};
export type CareRequest = {
  id: number;
  reference: string;
  service_name: string;
  service_id: number;
  zone: string;
  day: string;
  priority: string;
  status: string;
  provider: string | null;
  referral_id: number | null;
};
export type Recommendation = {
  facility_id: number;
  name: string;
  zone: string;
  available: number;
  local: boolean;
};
export type Dashboard = {
  facilities: number;
  available: number;
  active_referrals: number;
  completed: number;
  pending: number;
  gaps: {
    zone: string;
    service: string;
    pending: number;
    available: number;
    reason: string;
  }[];
  budget: { total: number; committed: number; remaining: number };
};
export type Plan = {
  id: number;
  day: string;
  cost: number;
  units: number;
  status: string;
  allocations: {
    facility_name: string;
    service_name: string;
    zone: string;
    units: number;
    unit_cost: number;
  }[];
};
export type Config = {
  today: string;
  zones: string[];
  demo_reset_enabled: boolean;
};

export const API = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).replace(/\/$/, "");

export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    method,
    cache: "no-store",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(20000),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = data.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg: string }) => d.msg).join(". ")
          : "The server could not complete this action",
    );
  }
  return response.json();
}

export function money(value: number) {
  return new Intl.NumberFormat("en-PK", { maximumFractionDigits: 0 }).format(
    value,
  );
}
