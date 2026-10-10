"use client";
import { useEffect, useState, FormEvent, ReactNode } from "react";
import {
  Activity,
  Building2,
  MapPin,
  ArrowRight,
  LogOut,
  Network,
  ClipboardList,
  Wallet,
  ShieldCheck,
  RefreshCw,
  Download,
  Check,
  Plus,
  X,
} from "lucide-react";
import {
  api,
  ApiError,
  API,
  human,
  hospitalName,
  money,
  State,
  User,
  Facility,
  CareRequest,
  Referral,
  Recommendation,
  RecommendationResult,
  Match,
  Plan,
  RankingPolicy,
} from "@/lib/api";
import { GovernmentOverview } from "@/components/government-overview";
import { HospitalCatalog } from "@/components/hospital-catalog";
import { MonthlyOutcomes } from "@/components/monthly-outcomes";
import { Dialog } from "@/components/dialog";
import { PlanRevision } from "@/components/plan-revision";
import { GuidedDemo } from "@/components/guided-demo";
import {
  AllocationDecisionTrace,
  MatchDecisionTrace,
  ReferralDecisionTrace,
} from "@/components/decision-traces";

type Field = {
  name: string;
  label: string;
  value?: string | number | boolean;
  type?: string;
  options?: { value: string; label: string }[];
  required?: boolean;
  autoComplete?: string;
};
function Form({
  fields,
  onSubmit,
  submit = "Save",
  busy = false,
}: {
  fields: Field[];
  onSubmit: (data: Record<string, string | boolean>) => Promise<void>;
  submit?: string;
  busy?: boolean;
}) {
  return (
    <form
      onSubmit={async (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const form = e.currentTarget;
        const raw = new FormData(form);
        const data: Record<string, string | boolean> = {};
        fields.forEach(
          (f) =>
            (data[f.name] =
              f.type === "checkbox"
                ? raw.has(f.name)
                : String(raw.get(f.name) || "")),
        );
        await onSubmit(data);
      }}
    >
      <div className="fields">
        {fields.map((f) => (
          <label
            key={f.name}
            className={f.type === "checkbox" ? "check-field" : ""}
          >
            {f.type === "checkbox" ? (
              <>
                <input
                  name={f.name}
                  type="checkbox"
                  defaultChecked={Boolean(f.value)}
                />
                <span>{f.label}</span>
              </>
            ) : (
              <>
                <span>{f.label}</span>
                {f.options ? (
                  <select
                    name={f.name}
                    aria-label={f.label}
                    defaultValue={String(f.value ?? "")}
                    required={f.required !== false}
                  >
                    {f.options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    name={f.name}
                    type={f.type || "text"}
                    autoComplete={f.autoComplete}
                    autoCapitalize={f.name === "username" ? "none" : undefined}
                    spellCheck={f.name === "username" ? false : undefined}
                    defaultValue={String(f.value ?? "")}
                    required={f.required !== false}
                    min={f.type === "number" ? 0 : undefined}
                  />
                )}
              </>
            )}
          </label>
        ))}
      </div>
      <button className="primary" disabled={busy}>
        {busy ? "Working…" : submit}
        <ArrowRight size={15} />
      </button>
    </form>
  );
}
function Badge({ value }: { value: string }) {
  return <span className={`badge ${value.toLowerCase()}`}>{human(value)}</span>;
}
function Card({
  title,
  children,
  aside,
}: {
  title: string;
  children: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <section className="card">
      <div className="card-title">
        <h2>{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}
export default function Home() {
  const [ranking, setRanking] = useState<RankingPolicy | null>(null);
  const [revisionPlan, setRevisionPlan] = useState<Plan | null>(null);
  const [reasonAction, setReasonAction] = useState<{
    path: string;
    body: Record<string, unknown>;
    method: string;
    resolve: (value: unknown) => void;
    reject: (reason: Error) => void;
  } | null>(null);
  const [reasonSaving, setReasonSaving] = useState(false),
    [reasonError, setReasonError] = useState("");

  const [token, setToken] = useState(""),
    [state, setState] = useState<State | null>(null),
    [screen, setScreen] = useState("network"),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [selected, setSelected] = useState<string | null>(null),
    [month, setMonth] = useState(""),
    [day, setDay] = useState("");
  const [request, setRequest] = useState<CareRequest | null>(null),
    [options, setOptions] = useState<Recommendation[]>([]),
    [reasons, setReasons] = useState<string[]>([]),
    [recommendationResult, setRecommendationResult] =
      useState<RecommendationResult | null>(null),
    [match, setMatch] = useState<Match | null>(null),
    [reviewId, setReviewId] = useState(""),
    [description, setDescription] = useState("general doctor consultation"),
    [matchKind, setMatchKind] = useState<"service" | "facility">("service"),
    [plan, setPlan] = useState<Plan | null>(null);
  useEffect(() => {
    setToken(sessionStorage.getItem("sehat-token") || "");
  }, []);
  async function load(auth = token) {
    if (!auth) return;
    const data = await api<State>(
      `state${month || day ? `?month=${month || state?.config.month}&date=${day || state?.config.service_date}` : ""}`,
      auth,
    );
    setState(data);
    setPlan((p) => (p ? data.plans.find((x) => x.id === p.id) || p : null));
    if (data.user.role === "planner") {
      setRanking(await api<RankingPolicy>("referral-ranking", auth));
    }
  }
  useEffect(() => {
    if (token)
      load().catch((e) => {
        setError(e.message);
        if (e instanceof ApiError && e.status === 401) {
          setToken("");
          sessionStorage.removeItem("sehat-token");
        }
      });
  }, [token, month, day]); // eslint-disable-line react-hooks/exhaustive-deps
  async function run(
    action: () => Promise<unknown>,
    message = "Saved. Related totals have been refreshed.",
  ) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      await load();
      setNotice(message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
      if (e instanceof ApiError && e.status === 401) {
        logout();
        setError("Your session expired. Sign in again.");
      } else if (
        e instanceof ApiError &&
        ["STALE_INPUT", "CAPACITY_CONFLICT"].includes(e.code)
      ) {
        setOptions([]);
        await load().catch(() => {});
        setError(
          `${e.message}. Current inputs have been refreshed; review and retry. For referrals, find providers again.`,
        );
      }
    } finally {
      setBusy(false);
    }
  }
  async function mutate(path: string, body: unknown = {}, method = "POST") {
    const data = body as Record<string, unknown>;
    if (
      data?.reason &&
      (/\/(cancel|reject|no-show|reprocess|participation)$/.test(path) ||
        (path.endsWith("partner-response") && data.accepted === false))
    ) {
      setReasonError("");
      return new Promise((resolve, reject) =>
        setReasonAction({ path, body: data, method, resolve, reject }),
      );
    }
    return api<unknown>(path, token, method, body);
  }
  async function login(data: Record<string, string | boolean>) {
    setBusy(true);
    setError("");
    try {
      const result = await api<{ token: string; user: User }>(
        "auth/login",
        "",
        "POST",
        { username: String(data.username).trim(), password: data.password },
      );
      logout();
      sessionStorage.setItem("sehat-token", result.token);
      setToken(result.token);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function logout() {
    setToken("");
    setState(null);
    setPlan(null);
    setRevisionPlan(null);
    setMatch(null);
    setRequest(null);
    setOptions([]);
    setReasons([]);
    setReviewId("");
    setRanking(null);
    setSelected(null);
    setScreen("network");
    setMonth("");
    setDay("");
    setNotice("");
    sessionStorage.removeItem("sehat-token");
  }
  if (!token || !state)
    return (
      <main className="login">
        <div className="login-intro">
          <div className="brand">
            <Activity />
            SEHAT GRID
          </div>
          <span className="eyebrow">ISLAMABAD · PRIMARY-CARE PILOT</span>
          <h1>
            A clearer view of care.
            <br />A better way to connect it.
          </h1>
          <p>
            See Islamabad’s hospital network in 3D. Coordinate referrals,
            onboard hospital services, and turn available resources into care.
          </p>
          <div className="login-pills">
            <span>01 Government representative</span>
            <span>02 Hospital reception</span>
            <span>03 Hospital onboarding</span>
          </div>
          <small>
            Synthetic demonstration · no patient login · no real payments
          </small>
          <div className="login-city" aria-hidden="true">
            {Array.from({ length: 24 }, (_, i) => (
              <i
                key={i}
                style={{
                  left: `${(i % 6) * 15 + 4}%`,
                  top: `${Math.floor(i / 6) * 19 + 6}%`,
                  height: `${22 + ((i * 13) % 50)}px`,
                  background:
                    i === 8 || i === 15
                      ? "#7c9ef4"
                      : i === 11 || i === 18
                        ? "#e9959a"
                        : "#e4e9ef",
                }}
              />
            ))}
          </div>
        </div>
        <div className="login-card">
          <ShieldCheck size={32} />
          <h2>Sign in to the pilot</h2>
          <p>Your account determines your role and assigned facility.</p>
          {error && (
            <div role="alert" className="error">
              {error}
            </div>
          )}
          {token ? (
            <>
              <p>Loading your workspace…</p>
              {error && (
                <div className="action-buttons">
                  <button disabled={busy} onClick={() => run(() => load())}>
                    Retry workspace
                  </button>
                  <button onClick={logout}>Sign out</button>
                </div>
              )}
            </>
          ) : (
            <Form
              busy={busy}
              onSubmit={login}
              submit="Sign in"
              fields={[
                {
                  name: "username",
                  label: "Username",
                  autoComplete: "username",
                },
                {
                  name: "password",
                  label: "Password",
                  type: "password",
                  autoComplete: "current-password",
                },
              ]}
            />
          )}
          <small>Use the password configured for this deployment.</small>
        </div>
      </main>
    );
  const planner = state.user.role === "planner",
    onboarder = state.user.role === "onboarder",
    own = state.facilities.filter((f) =>
      state.user.facility_ids.includes(f.id),
    ),
    facility =
      state.facilities.find((f) => f.id === selected) ||
      own[0] ||
      state.facilities[0],
    serviceDate = day || state.config.service_date,
    planningMonth = month || state.config.month;
  const canSend =
    state.user.role === "operator" &&
    own.some((f) => f.ownership === "Public" && f.participation === "ACTIVE");
  const facilityName = (id: string, fallback = id) => {
    const found = state.facilities.find((f) => f.id === id);
    return found ? hospitalName(found) : fallback;
  };
  const zones = state.config.zones.map((z) => ({ value: z.id, label: z.name })),
    facilityOptions = own
      .filter((f) => f.ownership === "Public" && f.participation === "ACTIVE")
      .map((f) => ({ value: f.id, label: hospitalName(f) }));
  const stats =
    planner && state.summary
      ? [
          ["Unresolved requests", state.summary.unresolved],
          ["Confirmed requests", state.summary.confirmed],
          ["Completed services", state.summary.completed],
          [
            "Monthly funds left",
            `PKR ${money(state.summary.budget?.remaining || 0)}`,
          ],
        ]
      : onboarder
        ? [
            ["Assigned hospitals", own.length],
            [
              "Catalog services",
              own.reduce((n, f) => n + (f.catalog?.length || 0), 0),
            ],
            [
              "Reviewed primary-care services",
              own.filter((f) => f.service_reviewed).length,
            ],
            [
              "Declared daily quota",
              own.reduce((n, f) => n + (f.capacities[0]?.quota || 0), 0),
            ],
          ]
        : [
            ["Assigned providers", own.length],
            [
              "Incoming referrals",
              state.referrals.filter(
                (a) =>
                  state.user.facility_ids.includes(a.facility_id) &&
                  ["AWAITING_CONFIRMATIONS", "CONFIRMED", "ARRIVED"].includes(
                    a.status,
                  ),
              ).length,
            ],
            [
              "Outgoing requests",
              state.requests.filter((r) =>
                state.user.facility_ids.includes(r.source_facility_id),
              ).length,
            ],
            [
              "Fresh quota remaining",
              own.reduce((n, f) => n + (f.capacities[0]?.available || 0), 0),
            ],
          ];
  async function recommend(r: CareRequest) {
    setRequest(r);
    setOptions([]);
    setReasons([]);
    setRecommendationResult(null);
    await run(async () => {
      const result = await api<RecommendationResult>(
        `requests/${r.id}/recommendations`,
        token,
      );
      setOptions(result.candidates);
      setReasons(result.reasons);
      setRecommendationResult(result);
    }, "Recommendations checked against current capacity and funding.");
  }
  async function exportPlan(p: Plan, format: string) {
    await run(async () => {
      const response = await fetch(
        `${API}/api/v1/plans/${p.id}/export?format=${format}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!response.ok) throw new Error("Export failed");
      const url = URL.createObjectURL(await response.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `sehat-grid-${p.id}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    }, "Plan summary downloaded. It contains aggregate allocations, not request identities.");
  }
  const profileFields = (f?: Facility): Field[] => [
    { name: "name", label: "Hospital name", value: f ? hospitalName(f) : "" },
    {
      name: "ownership",
      label: "Ownership",
      value: f?.ownership,
      options: f
        ? [{ value: f.ownership, label: `${f.ownership} (registered)` }]
        : [
            { value: "Public", label: "Public" },
            { value: "Private", label: "Private" },
          ],
    },
    { name: "address", label: "Address", value: f?.address },
    { name: "zone", label: "Pilot zone", value: f?.zone, options: zones },
    { name: "latitude", label: "Latitude", value: f?.latitude || 33.7 },
    { name: "longitude", label: "Longitude", value: f?.longitude || 73.05 },
  ];
  return (
    <div
      className={`app ${planner && screen === "network" ? "planner-city" : ""} ${onboarder ? "onboarding-app" : planner ? "government-app" : "reception-app"}`}
    >
      {revisionPlan && (
        <Dialog
          title={`Revise draft ${revisionPlan.id}`}
          close={() => setRevisionPlan(null)}
        >
          <PlanRevision
            plan={revisionPlan}
            token={token}
            facilityName={facilityName}
            onSaved={async (p) => {
              setPlan(p);
              setRevisionPlan(null);
              await load();
              setNotice(
                "Human draft revision saved. Totals reflect the validated selections.",
              );
            }}
          />
        </Dialog>
      )}
      {reasonAction && (
        <Dialog
          title="Record the operational reason"
          close={() => {
            reasonAction.reject(
              new Error("Action cancelled before submission."),
            );
            setReasonAction(null);
          }}
        >
          {reasonError && <p className="error">{reasonError}</p>}
          <Form
            busy={reasonSaving}
            fields={[
              {
                name: "reason",
                label: "Reason for this decision",
                value: String(reasonAction.body.reason),
              },
            ]}
            submit="Save decision"
            onSubmit={async (d) => {
              setReasonSaving(true);
              try {
                const result = await api(
                  reasonAction.path,
                  token,
                  reasonAction.method,
                  { ...reasonAction.body, reason: d.reason },
                );
                reasonAction.resolve(result);
                setReasonAction(null);
              } catch (e) {
                setReasonError((e as Error).message);
              } finally {
                setReasonSaving(false);
              }
            }}
          />
        </Dialog>
      )}

      <header>
        <a className="brand" href="/" aria-label="Sehat Grid home">
          <Activity />
          SEHAT GRID
        </a>
        <div className="header-scope">
          Islamabad <span> / </span> Primary-care pilot
        </div>
        <div className="account">
          <span>
            {own[0] &&
            /^P\d+ hospital (operator|onboarder)$/.test(state.user.name)
              ? hospitalName(own[0])
              : state.user.name}
          </span>
          <span className="role-label">
            {planner ? "Government" : onboarder ? "Onboarding" : "Reception"}
          </span>
          <button
            className="icon-button"
            onClick={logout}
            aria-label="Sign out"
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>
      <div className="demo-banner">
        <span>
          <i /> Islamabad hospital directory · Demo capacity & activity
        </span>
        <span>
          Non-emergency primary-care only · reported network quota, not hospital
          workload
        </span>
      </div>
      <GuidedDemo state={state} screen={screen} navigate={setScreen} />
      <div className="workspace">
        <aside className="sidebar">
          <span className="nav-label">WORKSPACE</span>
          {(onboarder
            ? [
                { id: "network", name: "Hospital setup", icon: Building2 },
                {
                  id: "catalog",
                  name: "Services & prices",
                  icon: ClipboardList,
                },
              ]
            : [
                {
                  id: "network",
                  name: planner ? "Network overview" : "Facility dashboard",
                  icon: Network,
                },
                {
                  id: "referrals",
                  name: planner
                    ? "Funding approvals"
                    : canSend
                      ? "Referral coordination"
                      : "Receiving desk",
                  icon: ClipboardList,
                },
                {
                  id: "intelligence",
                  name: planner ? "Unresolved demand" : "Matching & review",
                  icon: MapPin,
                },
                {
                  id: "planning",
                  name: planner ? "Monthly planner" : "Offers & activation",
                  icon: Wallet,
                },
                ...(planner
                  ? [
                      {
                        id: "outcomes",
                        name: "Monthly outcomes",
                        icon: Activity,
                      },
                    ]
                  : []),
              ]
          ).map((item) => (
            <button
              key={item.id}
              data-demo-nav={item.id}
              className={screen === item.id ? "active" : ""}
              onClick={() => {
                setScreen(item.id);
                setError("");
                setNotice("");
              }}
            >
              <item.icon size={18} />
              {item.name}
            </button>
          ))}
          <div className="sidebar-note">
            <ShieldCheck size={20} />
            <strong>One connected workflow</strong>
            <p>
              Review → reserve → confirm → complete.
              <br />
              Plan → approve → activate.
            </p>
            <small>
              Scope v{state.config.scope_version}
              <br />
              Asia/Karachi
            </small>
          </div>
        </aside>
        <main className="main">
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                {planner
                  ? "GOVERNMENT REPRESENTATIVE"
                  : onboarder
                    ? "HOSPITAL ONBOARDING"
                    : "HOSPITAL RECEPTION"}
              </span>
              <h1>
                {screen === "network"
                  ? planner
                    ? "Islamabad, connected."
                    : onboarder
                      ? "Build your hospital profile."
                      : "Welcome to reception."
                  : screen === "outcomes"
                    ? "From plans to patients."
                    : screen === "catalog"
                      ? "Every service, clearly listed."
                      : screen === "referrals"
                        ? planner
                          ? "Funding approvals"
                          : "Referral coordination"
                        : screen === "intelligence"
                          ? planner
                            ? "Recorded unmet network demand"
                            : "Review before routing"
                          : planner
                            ? "Make resources go further."
                            : "Offer resources. Activate care."}
              </h1>
              <p>
                {screen === "network"
                  ? planner
                    ? "Explore your hospital network."
                    : onboarder
                      ? "Keep your hospital details, service eligibility and daily capacity up to date."
                      : "Manage incoming patients and help every request find the right provider."
                  : screen === "planning"
                    ? "Monthly resources linked to dated, eligible unresolved requests."
                    : "Every decision is attributable, reviewed and recorded."}
              </p>
            </div>
            <div className="date-controls">
              <label>
                Service date
                <input
                  type="date"
                  value={serviceDate}
                  onChange={(e) => setDay(e.target.value)}
                />
              </label>
              <label>
                Planning month
                <input
                  type="month"
                  value={planningMonth}
                  onChange={(e) => setMonth(e.target.value)}
                />
              </label>
              <button
                className="icon-button"
                disabled={busy}
                onClick={() =>
                  run(() => load(), "Updated from the shared backend.")
                }
                aria-label="Refresh"
              >
                <RefreshCw size={18} />
              </button>
            </div>
          </div>
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              <Check size={16} />
              {notice}
            </div>
          )}
          <div className="stats">
            {stats.map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
                <small>
                  {planner ? planningMonth : "Current operational scope"}
                </small>
              </div>
            ))}
          </div>
          {planner && screen === "network" && (
            <GovernmentOverview
              state={state}
              selected={selected}
              onSelect={setSelected}
              navigate={setScreen}
              previousMonth={() => {
                const [year, m] = planningMonth.split("-").map(Number);
                const previous = new Date(Date.UTC(year, m - 2, 1))
                  .toISOString()
                  .slice(0, 7);
                setMonth(previous);
                setScreen("outcomes");
              }}
            />
          )}
          {planner && screen === "outcomes" && (
            <MonthlyOutcomes state={state} navigate={setScreen} />
          )}
          {!planner && !onboarder && screen === "network" && (
            <div className="reception-home">
              <Card
                title="Your reception desk"
                aside={<Badge value="ACTIVE" />}
              >
                <div className="reception-welcome">
                  <div className="reception-building">
                    <Building2 size={42} />
                  </div>
                  <div>
                    <span className="eyebrow">ASSIGNED HOSPITAL</span>
                    <h2>{own[0] ? hospitalName(own[0]) : "Your hospital"}</h2>
                    <p>{own[0]?.address}</p>
                    <button
                      className="primary"
                      onClick={() => setScreen("referrals")}
                    >
                      Open referral coordination
                      <ArrowRight size={15} />
                    </button>
                  </div>
                </div>
              </Card>
              <div className="two-col">
                <Card title="Incoming patients">
                  {state.referrals.filter(
                    (a) =>
                      state.user.facility_ids.includes(a.facility_id) &&
                      [
                        "AWAITING_CONFIRMATIONS",
                        "CONFIRMED",
                        "ARRIVED",
                      ].includes(a.status),
                  ).length ? (
                    state.referrals
                      .filter(
                        (a) =>
                          state.user.facility_ids.includes(a.facility_id) &&
                          [
                            "AWAITING_CONFIRMATIONS",
                            "CONFIRMED",
                            "ARRIVED",
                          ].includes(a.status),
                      )
                      .slice(0, 6)
                      .map((a) => (
                        <button
                          className="reception-referral"
                          key={a.id}
                          onClick={() => setScreen("referrals")}
                        >
                          <div>
                            <strong>
                              {state.requests.find((r) => r.id === a.request_id)
                                ?.reference || a.request_id}
                            </strong>
                            <span>{a.date} · Primary-care OPD</span>
                          </div>
                          <Badge value={a.status} />
                        </button>
                      ))
                  ) : (
                    <div className="empty">
                      <ClipboardList size={28} />
                      <p>No incoming referrals yet.</p>
                      <button onClick={() => setScreen("referrals")}>
                        View referral workspace
                      </button>
                    </div>
                  )}
                </Card>
                <Card title="Hospital availability">
                  {own.map((f) => (
                    <div key={f.id}>
                      <h3>{hospitalName(f)}</h3>
                      <div className="detail-metrics">
                        <div>
                          <strong>{f.capacities[0]?.available ?? "—"}</strong>
                          <span>Available slots</span>
                        </div>
                        <div>
                          <strong>{f.capacities[0]?.quota ?? "—"}</strong>
                          <span>Declared daily quota</span>
                        </div>
                      </div>
                      <p className="subtle">
                        {serviceDate} ·{" "}
                        {human(f.capacities[0]?.status || "UNKNOWN")}
                      </p>
                    </div>
                  ))}
                  <p className="subtle">
                    Hospital onboarding manages service prices and declared
                    capacity.
                  </p>
                  <button onClick={() => setScreen("intelligence")}>
                    Match a care request
                    <ArrowRight size={14} />
                  </button>
                </Card>
              </div>
            </div>
          )}
          {onboarder &&
            screen === "catalog" &&
            own.map((f) => (
              <HospitalCatalog
                key={f.id}
                facility={f}
                busy={busy}
                save={async (path, body, method) => {
                  let failed = false;
                  await run(async () => {
                    try {
                      await mutate(path, body, method);
                    } catch (e) {
                      failed = true;
                      throw e;
                    }
                  });
                  if (failed) throw new Error("Catalog update failed");
                }}
              />
            ))}
          {(screen === "providers" || (screen === "network" && onboarder)) && (
            <>
              <div className="network-layout">
                <Card
                  title="Participating providers"
                  aside={
                    <span className="count">
                      {onboarder ? own.length : state.facilities.length}
                    </span>
                  }
                >
                  <div className="provider-list">
                    {(onboarder ? own : state.facilities).map((f) => (
                      <button
                        key={f.id}
                        className={
                          facility?.id === f.id
                            ? "provider selected"
                            : "provider"
                        }
                        onClick={() => setSelected(f.id)}
                      >
                        <div className="provider-icon">
                          <Building2 size={20} />
                        </div>
                        <div>
                          <strong>{hospitalName(f)}</strong>
                          <span>
                            {f.zone} · {f.ownership}
                          </span>
                          <small>{f.address}</small>
                        </div>
                        <Badge value={f.capacities[0]?.status || "UNKNOWN"} />
                      </button>
                    ))}
                  </div>
                </Card>
                <Card
                  title={
                    onboarder ? "Onboarding checklist" : "Provider management"
                  }
                >
                  <div className="onboarding-checklist">
                    <p>
                      <Check size={17} />
                      Hospital identity and campus location
                    </p>
                    <p>
                      {own.every((f) => f.service_reviewed) ? (
                        <Check size={17} />
                      ) : (
                        <Plus size={17} />
                      )}
                      Primary-care service and eligible areas
                    </p>
                    <p>
                      {own.every(
                        (f) => f.capacities[0]?.freshness === "CURRENT",
                      ) ? (
                        <Check size={17} />
                      ) : (
                        <RefreshCw size={17} />
                      )}
                      Declared network capacity for each date
                    </p>
                    <p>
                      {own.some((f) => f.catalog?.length) ? (
                        <Check size={17} />
                      ) : (
                        <Plus size={17} />
                      )}
                      {own.some((f) => f.catalog?.length)
                        ? "Service and test prices added"
                        : "Add service and test prices"}
                    </p>
                  </div>
                  {onboarder && (
                    <button
                      className="primary"
                      onClick={() => setScreen("catalog")}
                    >
                      Manage services & prices
                      <ArrowRight size={15} />
                    </button>
                  )}
                  {planner && (
                    <button onClick={() => setScreen("network")}>
                      Back to 3D network
                    </button>
                  )}
                </Card>
              </div>
              {facility && (
                <Card
                  title={hospitalName(facility)}
                  aside={<Badge value={facility.participation} />}
                >
                  <div className="profile-grid">
                    <div>
                      <p>{facility.address}</p>
                      <p>
                        Declared eligible zones:{" "}
                        {facility.eligible_zones.join(", ") || "None yet"}
                      </p>
                      <p>
                        {facility.latitude.toFixed(6)},{" "}
                        {facility.longitude.toFixed(6)}
                      </p>
                      {facility.directory_context && (
                        <div className="provenance">
                          <strong>{facility.directory_context.name}</strong>
                          <p>
                            {facility.directory_context.label}. The name and
                            campus point are public context; quotas, agreements
                            and funding below are synthetic.
                          </p>
                          <a
                            target="_blank"
                            rel="noreferrer"
                            href={
                              facility.directory_context.profile
                                .coordinate_source
                            }
                          >
                            Coordinate source ↗
                          </a>
                        </div>
                      )}
                    </div>
                    <div>
                      {facility.capacities.map((c) => (
                        <div key={c.id} className="quota-detail">
                          <Badge value={c.status} />
                          <h3>
                            {c.available ?? "Unknown"} available / {c.quota}{" "}
                            declared
                          </h3>
                          <p>
                            {c.held} held · {c.committed} committed ·{" "}
                            {c.completed} completed · {c.forfeited} forfeited
                          </p>
                          <small>
                            {c.date} · Updated{" "}
                            {new Date(c.updated_at).toLocaleString("en-PK", {
                              timeZone: "Asia/Karachi",
                            })}{" "}
                            PKT · {human(c.freshness)}
                          </small>
                        </div>
                      ))}
                      {!facility.capacities.length && (
                        <p className="empty">
                          No quota in your scope for this date.
                        </p>
                      )}
                      {planner ? (
                        <button
                          disabled={busy}
                          onClick={() =>
                            run(() =>
                              mutate(
                                `facilities/${facility.id}/participation`,
                                {
                                  status:
                                    facility.participation === "ACTIVE"
                                      ? "SUSPENDED"
                                      : "ACTIVE",
                                  version: facility.version,
                                  reason:
                                    "Planner reviewed demonstration participation",
                                },
                              ),
                            )
                          }
                        >
                          {facility.participation === "ACTIVE"
                            ? "Suspend participation"
                            : "Activate participation"}
                        </button>
                      ) : (
                        state.user.facility_ids.includes(facility.id) && (
                          <Form
                            key={
                              facility.id +
                              serviceDate +
                              (facility.capacities[0]?.version || 0)
                            }
                            busy={busy}
                            submit="Update dated quota"
                            fields={[
                              {
                                name: "quota",
                                label: "Declared network quota",
                                type: "number",
                                value: facility.capacities[0]?.quota || 0,
                              },
                            ]}
                            onSubmit={(d) =>
                              run(() =>
                                mutate(
                                  `facilities/${facility.id}/capacity/PRIMARY_CARE_OPD/${serviceDate}`,
                                  {
                                    quota: Number(d.quota),
                                    version:
                                      facility.capacities[0]?.version || 0,
                                  },
                                  "PUT",
                                ),
                              )
                            }
                          />
                        )
                      )}
                    </div>
                  </div>
                </Card>
              )}
              {onboarder && (
                <div className="two-col">
                  <Card title="Register a provider">
                    <Form
                      fields={profileFields()}
                      busy={busy}
                      submit="Register for planner review"
                      onSubmit={(d) =>
                        run(() =>
                          mutate("facilities", {
                            ...d,
                            latitude: Number(d.latitude),
                            longitude: Number(d.longitude),
                          }),
                        )
                      }
                    />
                  </Card>
                  <Card title="Own provider settings">
                    {own.map((f) => (
                      <details key={f.id} open>
                        <summary>{hospitalName(f)}</summary>
                        <Form
                          fields={profileFields(f)}
                          busy={busy}
                          submit="Update profile"
                          onSubmit={(d) =>
                            run(() =>
                              mutate(
                                `facilities/${f.id}`,
                                {
                                  ...d,
                                  latitude: Number(d.latitude),
                                  longitude: Number(d.longitude),
                                  version: f.version,
                                },
                                "PATCH",
                              ),
                            )
                          }
                        />
                        <Form
                          key={f.id + f.version}
                          fields={[
                            {
                              name: "zones",
                              label: "Eligible zones (comma separated)",
                              value: f.eligible_zones.join(", "),
                            },
                            {
                              name: "subsidy",
                              label:
                                "Requires subsidy for funding-eligible requests",
                              type: "checkbox",
                              value: f.subsidy_required,
                            },
                          ]}
                          busy={busy}
                          submit="Confirm primary-care service"
                          onSubmit={(d) =>
                            run(() =>
                              mutate(`facilities/${f.id}/services`, {
                                service_id: "PRIMARY_CARE_OPD",
                                eligible_zones: String(d.zones)
                                  .split(",")
                                  .map((z) => z.trim())
                                  .filter(Boolean),
                                reviewed: true,
                                subsidy_required: d.subsidy,
                                version: f.version,
                              }),
                            )
                          }
                        />
                      </details>
                    ))}
                  </Card>
                </div>
              )}
            </>
          )}
          {screen === "referrals" && (
            <>
              {planner && ranking && (
                <Card title="Referral ranking policy">
                  <p>
                    {ranking.policy_version}. Eligibility checks always apply.
                    Equal scores use provider ID and date.
                  </p>
                  <Form
                    key={ranking.version}
                    busy={busy}
                    submit="Save referral ranking"
                    fields={[
                      {
                        name: "criteria",
                        label: "Preferred order",
                        value: ranking.criteria.join(","),
                        options: [
                          ["same_zone", "subsidy", "available"],
                          ["same_zone", "available", "subsidy"],
                          ["subsidy", "same_zone", "available"],
                          ["subsidy", "available", "same_zone"],
                          ["available", "same_zone", "subsidy"],
                          ["available", "subsidy", "same_zone"],
                        ].map((order) => ({
                          value: order.join(","),
                          label: order
                            .map(
                              (c) =>
                                ({
                                  same_zone: "Same zone",
                                  subsidy: "Lower subsidy",
                                  available: "More quota",
                                })[c],
                            )
                            .join(" → "),
                        })),
                      },
                      { name: "reason", label: "Reason for ranking change" },
                    ]}
                    onSubmit={(d) =>
                      run(() =>
                        mutate(
                          "referral-ranking",
                          {
                            criteria: String(d.criteria).split(","),
                            version: ranking.version,
                            reason: d.reason,
                          },
                          "PUT",
                        ),
                      )
                    }
                  />
                </Card>
              )}
              {planner && (
                <Card title="Hospital routing points">
                  <p>
                    Score = 60 × available quota fraction + 40 × government
                    preference / 100. Scores refresh as reservations change; no
                    hospital needs to be full before another is recommended.
                    Existing ranking criteria break ties. Eligibility and
                    required tests always apply.
                  </p>
                  <div className="policy-grid">
                    {state.facilities.map((f) => (
                      <section key={f.id} className="policy-hospital">
                        <h3>{hospitalName(f)}</h3>
                        <p>
                          {f.routing_metrics?.completed ?? 0} completed /{" "}
                          {f.routing_metrics?.referrals ?? 0} referrals ·
                          Closed-referral completion{" "}
                          {f.routing_metrics?.completion_rate == null
                            ? "not yet measured"
                            : `${f.routing_metrics.completion_rate}%`}
                        </p>
                        <Form
                          key={f.version}
                          busy={busy}
                          submit="Save points"
                          fields={[
                            {
                              name: "points",
                              label: "Government preference (0–100)",
                              type: "number",
                              value: f.routing_points ?? 50,
                            },
                            { name: "reason", label: "Reason for preference" },
                          ]}
                          onSubmit={(d) =>
                            run(() =>
                              mutate(
                                `facilities/${f.id}/routing-points`,
                                { ...d, version: f.version },
                                "PUT",
                              ),
                            )
                          }
                        />
                      </section>
                    ))}
                  </div>
                </Card>
              )}
              {!planner && !canSend && (
                <Card title="Receiving hospital workspace">
                  <p>
                    Accept or decline incoming referrals, record patient
                    agreement, arrival and completion. Only approved government
                    hospitals can originate and reroute patients. Contact the
                    sending hospital when a new destination is needed.
                  </p>
                </Card>
              )}
              {!planner && (
                <Card title="WhatsApp patient updates">
                  <button
                    className="primary"
                    onClick={() => window.open("/patient-updates", "_blank")}
                  >
                    Open patient message demo ↗
                  </button>
                  <p>
                    Consent-based message previews. Live WhatsApp delivery is
                    not connected; these messages have not been sent.
                  </p>
                  {state.notifications?.length ? (
                    state.notifications.map((n) => (
                      <div className="notification-preview" key={n.id}>
                        <strong>{n.recipient} · Preview only</strong>
                        <p>{n.message}</p>
                      </div>
                    ))
                  ) : (
                    <p className="empty">
                      Updates appear after a consented referral is confirmed or
                      cancelled.
                    </p>
                  )}
                </Card>
              )}
              {canSend && (
                <div className="two-col">
                  <Card title="Register a synthetic request">
                    <p>
                      Review the service description before using it for
                      referral eligibility.
                    </p>
                    <label className="standalone-label">
                      Service description
                      <input
                        value={description}
                        onChange={(e) => {
                          setDescription(e.target.value);
                          setReviewId("");
                          setMatch(null);
                        }}
                      />
                    </label>
                    <button
                      disabled={busy}
                      onClick={() =>
                        run(async () => {
                          setMatchKind("service");
                          setMatch(
                            await api<Match>(
                              "matching/services",
                              token,
                              "POST",
                              { text: description },
                            ),
                          );
                          setReviewId("");
                        }, "Review the suggested category before creating the request.")
                      }
                    >
                      Suggest service category
                    </button>
                    {match && matchKind === "service" && (
                      <div className="matching">
                        <Badge value={match.status} />
                        <MatchDecisionTrace
                          match={match}
                          state={state}
                          reviews={state.reviews}
                        />
                        {match.candidates.map((c, index) => (
                          <button
                            key={c.id}
                            disabled={busy || !!reviewId}
                            onClick={() =>
                              run(async () => {
                                const r = await api<{ id: string }>(
                                  "matching/reviews",
                                  token,
                                  "POST",
                                  {
                                    match_id: match.id,
                                    decision:
                                      match.status === "NEEDS_REVIEW" &&
                                      index === 0
                                        ? "ACCEPT"
                                        : "CORRECT",
                                    candidate_id: c.id,
                                    reason:
                                      "Operator reviewed primary-care description",
                                  },
                                );
                                setReviewId(r.id);
                              }, "Service review saved.")
                            }
                          >
                            <Check size={14} />
                            {match.status === "NEEDS_REVIEW" && index === 0
                              ? `Accept suggestion: ${facilityName(c.id, c.name)}`
                              : `Correct to: ${facilityName(c.id, c.name)}`}
                          </button>
                        ))}
                        <button
                          disabled={busy || !!reviewId}
                          onClick={() =>
                            run(async () => {
                              const r = await api<{ id: string }>(
                                "matching/reviews",
                                token,
                                "POST",
                                {
                                  match_id: match.id,
                                  decision: "DECLINE",
                                  candidate_id: null,
                                  reason:
                                    "Operator declined the suggested service",
                                },
                              );
                              setReviewId(r.id);
                            }, "Decline recorded as a human decision.")
                          }
                        >
                          Decline suggestion
                        </button>
                        <small>
                          {reviewId
                            ? "Human review recorded"
                            : "Choose accept, correct, or decline. No match is approved automatically."}
                        </small>
                      </div>
                    )}
                    <Form
                      busy={busy}
                      submit="Register request"
                      fields={[
                        {
                          name: "reference",
                          label: "Patient reference",
                          value: `DEMO-${state.requests.length + 1}`,
                        },
                        {
                          name: "source_facility_id",
                          label: "Originating provider",
                          options: facilityOptions,
                        },
                        { name: "zone", label: "Pilot zone", options: zones },
                        {
                          name: "required_tests_text",
                          label:
                            "Required tests or facilities (comma-separated catalog names)",
                          required: false,
                        },
                        {
                          name: "whatsapp_phone",
                          label: "WhatsApp number (+923001234567)",
                          type: "tel",
                          required: false,
                        },
                        {
                          name: "whatsapp_consent",
                          label:
                            "Patient agrees to WhatsApp referral updates, including service names",
                          type: "checkbox",
                        },
                        {
                          name: "date_from",
                          label: "From",
                          type: "date",
                          value: serviceDate,
                        },
                        {
                          name: "date_to",
                          label: "To",
                          type: "date",
                          value: serviceDate,
                        },
                        {
                          name: "suitable",
                          label:
                            "Authorized staff established non-emergency primary-care suitability",
                          type: "checkbox",
                        },
                        {
                          name: "needs_funding",
                          label: "Request needs funding support",
                          type: "checkbox",
                        },
                        {
                          name: "funding_eligible",
                          label: "Operational funding eligibility confirmed",
                          type: "checkbox",
                        },
                      ]}
                      onSubmit={({ required_tests_text, ...d }) =>
                        run(() =>
                          mutate("requests", {
                            ...d,
                            required_tests: String(required_tests_text || "")
                              .split(",")
                              .map((t) => t.trim())
                              .filter(Boolean),
                            original_text: description,
                            review_id: reviewId || null,
                          }),
                        )
                      }
                    />
                  </Card>
                  <Card
                    title="Recommendations"
                    aside={request && <Badge value={request.status} />}
                  >
                    <p>
                      {request
                        ? `${request.reference} · ${request.zone}`
                        : "Select a request below to find eligible destinations."}
                    </p>
                    {reasons.map((r) => (
                      <div className="empty" key={r}>
                        {human(r)}
                      </div>
                    ))}
                    {request && (
                      <ReferralDecisionTrace
                        request={request}
                        result={recommendationResult}
                        state={state}
                      />
                    )}
                    {options.map((o) => (
                      <div
                        key={o.capacity_id}
                        className="recommendation"
                        data-facility={o.facility_id}
                      >
                        <strong>{facilityName(o.facility_id, o.name)}</strong>
                        <p>{o.explanation}</p>
                        <small>
                          Routing score {o.routing_score}/100 · Government
                          preference {o.routing_points}/100 ·{" "}
                          {o.ranking_policy_version}
                        </small>
                        <span>
                          {o.date} · {o.available} units · Subsidy PKR{" "}
                          {money(o.subsidy)}
                        </span>
                        <button
                          className="primary"
                          disabled={busy}
                          onClick={() =>
                            run(async () => {
                              await mutate("referrals/proposals", {
                                request_id: request!.id,
                                capacity_id: o.capacity_id,
                                capacity_version: o.capacity_version,
                                facility_version: o.facility_version,
                              });
                              setOptions([]);
                              setReasons([]);
                              setRecommendationResult(null);
                            }, "Proposal saved. Review it below before reserving; no quota or funding has been held.")
                          }
                        >
                          Save referral proposal
                        </button>
                      </div>
                    ))}
                  </Card>
                </div>
              )}
              {!planner && (
                <Card title="Request queue">
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Request</th>
                          <th>Service dates</th>
                          <th>Zone</th>
                          <th>Status / reason</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {state.requests.map((r) => (
                          <tr key={r.id} data-demo-request={r.id}>
                            <td>
                              <strong>{r.reference}</strong>
                              <small>{r.original_text}</small>
                            </td>
                            <td>
                              {r.date_from}
                              <small>to {r.date_to}</small>
                            </td>
                            <td>{r.zone}</td>
                            <td>
                              <Badge value={r.status} />
                              <small>{r.reasons.map(human).join(", ")}</small>
                            </td>
                            <td>
                              {canSend &&
                                state.user.facility_ids.includes(
                                  r.source_facility_id,
                                ) &&
                                ![
                                  "FULFILLED",
                                  "CANCELLED",
                                  "IN_PROGRESS",
                                ].includes(r.status) && (
                                  <>
                                    <button
                                      disabled={busy}
                                      onClick={() => recommend(r)}
                                    >
                                      Find providers
                                    </button>
                                    <button
                                      disabled={busy}
                                      onClick={() =>
                                        run(() =>
                                          mutate(`requests/${r.id}/reprocess`, {
                                            reason:
                                              "Operator reviewed the request for another eligible option",
                                          }),
                                        )
                                      }
                                    >
                                      Reprocess
                                    </button>
                                    <button
                                      disabled={busy}
                                      onClick={() =>
                                        run(() =>
                                          mutate(`requests/${r.id}/cancel`, {
                                            reason:
                                              "Operator cancelled synthetic request",
                                          }),
                                        )
                                      }
                                    >
                                      Cancel
                                    </button>
                                  </>
                                )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
              <Card
                title={
                  planner
                    ? "Subsidy authorization queue"
                    : "Incoming & outgoing referrals"
                }
              >
                <div className="referral-list">
                  {state.referrals
                    .filter((a) =>
                      planner
                        ? a.status === "AWAITING_CONFIRMATIONS" && a.subsidy > 0
                        : !["COMPLETED"].includes(a.status),
                    )
                    .map((a) => {
                      const receive = state.user.facility_ids.includes(
                        a.facility_id,
                      );
                      const send =
                        canSend &&
                        state.requests.some(
                          (r) =>
                            r.id === a.request_id &&
                            state.user.facility_ids.includes(
                              r.source_facility_id,
                            ),
                        );
                      return (
                        <div className="referral" key={a.id} data-demo-referral={a.request_id}>
                          <div>
                            <strong>
                              {a.id} → {facilityName(a.facility_id)}
                            </strong>
                            <p>
                              {a.request_id} · {a.date} · Subsidy PKR{" "}
                              {money(a.subsidy)}
                            </p>
                            {!planner && (
                              <div className="referral-context">
                                <strong>
                                  {state.requests.find(
                                    (r) => r.id === a.request_id,
                                  )?.reference || a.request_id}
                                </strong>
                                <span>
                                  {state.requests.find(
                                    (r) => r.id === a.request_id,
                                  )?.original_text ||
                                    "Reviewed primary-care OPD"}
                                </span>
                                <span>
                                  {
                                    state.requests.find(
                                      (r) => r.id === a.request_id,
                                    )?.zone
                                  }{" "}
                                  ·{" "}
                                  {receive
                                    ? "Incoming patient"
                                    : "Outgoing referral"}
                                </span>
                              </div>
                            )}
                            <Badge value={a.status} />
                            <small>
                              Partner{" "}
                              {a.partner_accepted ? "accepted" : "pending"} ·
                              Patient {a.patient_agreed ? "agreed" : "pending"}{" "}
                              · Funding{" "}
                              {a.funding_approved ? "authorized" : "pending"}
                            </small>
                            {a.status === "AWAITING_CONFIRMATIONS" && (
                              <small>
                                Response deadline{" "}
                                {new Date(a.expires_at!).toLocaleString(
                                  "en-PK",
                                  { timeZone: "Asia/Karachi" },
                                )}{" "}
                                PKT
                              </small>
                            )}
                            {a.reason && <small>{a.reason}</small>}
                            {a.status === "PROPOSED" && (
                              <small>
                                Proposal only; no quota or funds held. If the
                                inputs change, the proposal expires and the
                                request reopens so you can select a fresh
                                destination.
                              </small>
                            )}
                          </div>
                          <div className="action-buttons">
                            {!planner && send && a.status === "PROPOSED" && (
                              <>
                                <button
                                  className="primary"
                                  disabled={busy}
                                  onClick={() =>
                                    run(async () => {
                                      const result = (await mutate(
                                        `referrals/${a.id}/reserve`,
                                      )) as Referral;
                                      if (result.status === "EXPIRED") {
                                        setOptions([]);
                                        await load();
                                        throw new Error(
                                          "This proposal expired because its inputs changed. The request is open again; find providers and choose a fresh destination.",
                                        );
                                      }
                                    }, "Temporary hold created. Partner acceptance and patient agreement are pending.")
                                  }
                                >
                                  Approve & reserve proposal
                                </button>
                                <button
                                  disabled={busy}
                                  onClick={() =>
                                    run(() =>
                                      mutate(`referrals/${a.id}/cancel`, {
                                        reason:
                                          "Sender cancelled the proposed destination",
                                      }),
                                    )
                                  }
                                >
                                  Cancel proposal
                                </button>
                              </>
                            )}
                            {a.status === "AWAITING_CONFIRMATIONS" &&
                              (planner ? (
                                <button
                                  disabled={busy || a.funding_approved}
                                  onClick={() =>
                                    run(() =>
                                      mutate(
                                        `referrals/${a.id}/funding-approval`,
                                        { accepted: true },
                                      ),
                                    )
                                  }
                                >
                                  Authorize funding
                                </button>
                              ) : (
                                <>
                                  {receive && (
                                    <>
                                      <button
                                        disabled={busy || a.partner_accepted}
                                        onClick={() =>
                                          run(() =>
                                            mutate(
                                              `referrals/${a.id}/partner-response`,
                                              { accepted: true },
                                            ),
                                          )
                                        }
                                      >
                                        Accept referral
                                      </button>
                                      <button
                                        disabled={busy}
                                        onClick={() =>
                                          run(() =>
                                            mutate(
                                              `referrals/${a.id}/partner-response`,
                                              {
                                                accepted: false,
                                                reason:
                                                  "Receiving operator declined the demonstration referral",
                                              },
                                            ),
                                          )
                                        }
                                      >
                                        Reject
                                      </button>
                                    </>
                                  )}
                                  <button
                                    disabled={busy || a.patient_agreed}
                                    onClick={() =>
                                      run(() =>
                                        mutate(
                                          `referrals/${a.id}/patient-agreement`,
                                          { accepted: true },
                                        ),
                                      )
                                    }
                                  >
                                    Record patient agreement
                                  </button>
                                  <button
                                    disabled={busy}
                                    onClick={() =>
                                      run(() =>
                                        mutate(
                                          `referrals/${a.id}/patient-agreement`,
                                          {
                                            accepted: false,
                                            reason:
                                              "Patient declined this option",
                                          },
                                        ),
                                      )
                                    }
                                  >
                                    Patient declined
                                  </button>
                                </>
                              ))}
                            {!planner &&
                              receive &&
                              a.status === "CONFIRMED" && (
                                <>
                                  <button
                                    disabled={busy}
                                    onClick={() =>
                                      run(() =>
                                        mutate(`referrals/${a.id}/arrival`),
                                      )
                                    }
                                  >
                                    Record arrival
                                  </button>
                                  <button
                                    disabled={busy}
                                    onClick={() =>
                                      run(() =>
                                        mutate(`referrals/${a.id}/no-show`, {
                                          reason:
                                            "Did not attend the declared service date",
                                        }),
                                      )
                                    }
                                  >
                                    No-show
                                  </button>
                                </>
                              )}
                            {!planner && receive && a.status === "ARRIVED" && (
                              <button
                                className="primary"
                                disabled={busy}
                                onClick={() =>
                                  run(() =>
                                    mutate(`referrals/${a.id}/completion`),
                                  )
                                }
                              >
                                Complete service
                              </button>
                            )}
                            {!planner &&
                              [
                                "AWAITING_CONFIRMATIONS",
                                "CONFIRMED",
                                "ARRIVED",
                              ].includes(a.status) && (
                                <button
                                  disabled={busy}
                                  onClick={() =>
                                    run(() =>
                                      mutate(`referrals/${a.id}/cancel`, {
                                        reason:
                                          "Operator cancelled synthetic referral",
                                      }),
                                    )
                                  }
                                >
                                  Cancel referral
                                </button>
                              )}
                          </div>
                        </div>
                      );
                    })}
                  {!state.referrals.some((a) =>
                    planner
                      ? a.status === "AWAITING_CONFIRMATIONS" && a.subsidy > 0
                      : a.status !== "COMPLETED",
                  ) && (
                    <p className="empty">
                      No referrals need action in this view.
                    </p>
                  )}
                </div>
              </Card>
            </>
          )}
          {screen === "intelligence" && (
            <>
              {planner && state.summary ? (
                <>
                  <div className="two-col">
                    <Card title="Unresolved platform requests">
                      <p>
                        Unique request units in {planningMonth}. Failed attempts
                        are not counted as additional demand.
                      </p>
                      {state.summary.zones.map((z) => (
                        <div className="zone-row" key={z.zone}>
                          <div>
                            <strong>{z.zone}</strong>
                            <small>
                              {Object.entries(z.reasons)
                                .map(([r, n]) => `${human(r)}: ${n}`)
                                .join(" · ") || "No unresolved requests"}
                            </small>
                          </div>
                          <b>{z.count}</b>
                        </div>
                      ))}
                    </Card>
                    <Card title="Resolution funnel">
                      <div className="funnel">
                        {[
                          ["Registered", state.summary.registered],
                          ["Confirmed", state.summary.confirmed],
                          ["Arrived", state.summary.arrived],
                          ["Completed", state.summary.completed],
                        ].map(([l, n]) => (
                          <div key={l}>
                            <span>{l}</span>
                            <strong>{n}</strong>
                          </div>
                        ))}
                      </div>
                      <p>
                        These are recorded platform outcomes, not estimates of
                        all healthcare need. Pending referrals remain in the
                        confirmation denominator.
                      </p>
                    </Card>
                  </div>
                  <Card title="Record matching & canonical identity review">
                    <MatchingTools />
                  </Card>
                </>
              ) : (
                <Card title="Semantic record and service review">
                  <MatchingTools />
                </Card>
              )}
              <Card title="Review history">
                {state.reviews.length ? (
                  state.reviews
                    .slice(-10)
                    .reverse()
                    .map((r) => (
                      <div key={r.id} className="history">
                        <strong>{r.input_text}</strong>
                        <Badge value={r.decision} />
                        <small>
                          {r.candidate_id || "No supported match"} · {r.actor}
                        </small>
                      </div>
                    ))
                ) : (
                  <p className="empty">No human reviews recorded yet.</p>
                )}
              </Card>
            </>
          )}
          {screen === "planning" && (
            <>
              {planner ? (
                <>
                  <div className="two-col">
                    <Card title="Monthly resource budget">
                      <Form
                        key={
                          planningMonth +
                          state.budgets.find((b) => b.month === planningMonth)
                            ?.version
                        }
                        busy={busy}
                        submit="Authorize monthly budget"
                        fields={[
                          {
                            name: "authorized",
                            label: "Budget in integer PKR",
                            type: "number",
                            value:
                              state.budgets.find(
                                (b) => b.month === planningMonth,
                              )?.authorized || 25000,
                          },
                        ]}
                        onSubmit={(d) =>
                          run(() =>
                            mutate("budgets", {
                              month: planningMonth,
                              authorized: Number(d.authorized),
                              version:
                                state.budgets.find(
                                  (b) => b.month === planningMonth,
                                )?.version || 0,
                            }),
                          )
                        }
                      />
                      {state.budgets
                        .filter((b) => b.month === planningMonth)
                        .map((b) => (
                          <div className="ledger-totals" key={b.month}>
                            {(
                              [
                                "HELD",
                                "COMMITTED",
                                "SETTLED",
                                "remaining",
                              ] as const
                            ).map((k) => (
                              <div key={k}>
                                <span>{human(k)}</span>
                                <strong>PKR {money(b[k])}</strong>
                              </div>
                            ))}
                          </div>
                        ))}
                      <details>
                        <summary>Fixed subsidy schedule</summary>
                        <Form
                          busy={busy}
                          fields={[
                            {
                              name: "amount",
                              label: "Contribution per eligible service (PKR)",
                              type: "number",
                              value: state.subsidy_rule?.amount || 0,
                            },
                          ]}
                          onSubmit={(d) =>
                            run(() =>
                              mutate("subsidy-rules", {
                                month: planningMonth,
                                amount: Number(d.amount),
                                version: state.subsidy_rule!.version,
                              }),
                            )
                          }
                        />
                      </details>
                    </Card>
                    <Card title="Compute an allocation">
                      <span className="eyebrow">
                        SUBSIDY + PARTNER QUOTA + MOBILE CLINIC
                      </span>
                      <h3>Current requests. Dated resources. One budget.</h3>
                      <p>
                        Freeze the current unresolved demand, then compute a
                        feasible monthly allocation. Approval and operator
                        activation follow separately.
                      </p>
                      <button
                        className="primary"
                        disabled={busy}
                        onClick={() =>
                          run(async () => {
                            const snap = await api<{ id: string }>(
                              "intelligence/snapshots",
                              token,
                              "POST",
                              { month: planningMonth },
                            );
                            const p = await api<Plan>(
                              "plans/optimize",
                              token,
                              "POST",
                              { snapshot_id: snap.id },
                            );
                            setPlan(p);
                          }, "Draft computed from an immutable demand snapshot.")
                        }
                      >
                        {busy ? "Computing…" : "Create snapshot & optimize"}
                        <ArrowRight size={16} />
                      </button>
                      <small>
                        No future demand is forecast. Budget excludes active
                        holds, commitments and settled costs.
                      </small>
                    </Card>
                  </div>
                </>
              ) : (
                <div className="two-col">
                  <Card title="Offer additional partner quota">
                    <OfferForm kind="QUOTA" />
                  </Card>
                  <Card title="Offer a mobile-clinic deployment">
                    <OfferForm kind="MOBILE" />
                  </Card>
                </div>
              )}
              <Card title="Offered resources">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Offer</th>
                        <th>Provider / date</th>
                        <th>Units</th>
                        <th>Fixed cost</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {state.offers.map((o) => (
                        <tr key={o.id}>
                          <td>
                            {o.id}
                            <small>
                              {human(o.kind)} {o.site}
                            </small>
                          </td>
                          <td>
                            {facilityName(o.facility_id)}
                            <small>{o.date}</small>
                          </td>
                          <td>{o.units}</td>
                          <td>PKR {money(o.cost)}</td>
                          <td>
                            <Badge value={o.status} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
              {state.plans.length > 0 && (
                <Card title="Saved plans">
                  <div className="plan-tabs">
                    {state.plans
                      .slice()
                      .reverse()
                      .map((p) => (
                        <button
                          key={p.id}
                          className={plan?.id === p.id ? "selected" : ""}
                          onClick={() => setPlan(p)}
                        >
                          {p.id} · {human(p.status)} · PKR {money(p.cost)}
                        </button>
                      ))}
                  </div>
                </Card>
              )}
              {plan && (
                <Card
                  title={`Plan ${plan.id}`}
                  aside={<Badge value={plan.status} />}
                >
                  <div className="plan-metrics">
                    <div>
                      <span>Projected additional accommodation</span>
                      <strong>{plan.additional}</strong>
                    </div>
                    <div>
                      <span>Baseline feasible units</span>
                      <strong>{plan.baseline}</strong>
                    </div>
                    <div>
                      <span>Incremental cost</span>
                      <strong>PKR {money(plan.cost)}</strong>
                    </div>
                    <div>
                      <span>
                        {plan.decision_source === "HUMAN_REVISION"
                          ? "Original solver result"
                          : "Solver result"}
                      </span>
                      <strong>{human(plan.solver_status)}</strong>
                    </div>
                  </div>
                  {planner && (
                    <AllocationDecisionTrace plan={plan} token={token} />
                  )}
                  <p>
                    {plan.unresolved_remaining} eligible units remain
                    unresolved.{" "}
                    {plan.assignments.filter((a) => a.subsidy > 0).length}{" "}
                    subsidy assignments · subsidy total PKR{" "}
                    {money(plan.subsidy_cost)}.
                  </p>
                  {plan.decision_source === "HUMAN_REVISION" && (
                    <div className="notice">
                      Human revision · version {plan.version}. Original solver:{" "}
                      {plan.original_solver_result?.coverage} units / PKR{" "}
                      {money(plan.original_solver_result?.cost || 0)}. Current
                      selections are a human decision.
                    </div>
                  )}
                  {planner && !!plan.revisions?.length && (
                    <details>
                      <summary>Draft revision history</summary>
                      {plan.revisions.map((r) => (
                        <p key={r.version}>
                          Version {r.version} · {r.actor} · {r.reason}
                        </p>
                      ))}
                    </details>
                  )}
                  <div className="plan-actions">
                    {plan.actions.map((a) => (
                      <div key={a.id}>
                        <div>
                          <strong>
                            {a.offer_id} · {human(a.kind)}
                          </strong>
                          <p>PKR {money(a.cost)}</p>
                          <Badge value={a.status} />
                        </div>
                        {!planner && a.status === "PENDING_ACTIVATION" && (
                          <div className="action-buttons">
                            <button
                              className="primary"
                              disabled={busy}
                              onClick={() =>
                                run(
                                  () =>
                                    mutate(
                                      `plans/${plan.id}/actions/${a.id}/activate`,
                                    ),
                                  "Resource activated; dated capacity and the ledger have been updated.",
                                )
                              }
                            >
                              Confirm & activate offered resource
                            </button>
                            <button
                              disabled={busy}
                              onClick={() =>
                                run(() =>
                                  mutate(
                                    `plans/${plan.id}/actions/${a.id}/reject`,
                                    {
                                      reason:
                                        "Offered resource is no longer available",
                                    },
                                  ),
                                )
                              }
                            >
                              Reject offered resource
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  <details>
                    <summary>Assumptions and excluded demand</summary>
                    {plan.assumptions.map((a) => (
                      <p key={a}>{a}</p>
                    ))}
                    <p>
                      {Object.entries(plan.excluded)
                        .map(([k, n]) => `${human(k)}: ${n}`)
                        .join(" · ") || "No excluded units"}
                    </p>
                  </details>
                  {planner && (
                    <div className="action-buttons">
                      {plan.status === "DRAFT" && (
                        <>
                          <button
                            disabled={busy}
                            onClick={() => setRevisionPlan(plan)}
                          >
                            Revise draft with reason
                          </button>
                          <button
                            className="primary"
                            disabled={busy}
                            onClick={() =>
                              run(
                                () =>
                                  mutate(`plans/${plan.id}/approve`, {
                                    version: plan.version,
                                  }),
                                "Plan approved. Funds and offers reserved; partner/mobile actions await their operators.",
                              )
                            }
                          >
                            Approve plan
                          </button>
                        </>
                      )}
                      {["DRAFT", "APPROVED", "ACTIVE"].includes(
                        plan.status,
                      ) && (
                        <button
                          disabled={busy}
                          onClick={() =>
                            run(() =>
                              mutate(`plans/${plan.id}/cancel`, {
                                reason:
                                  "Planner closed remaining unactivated commitments",
                              }),
                            )
                          }
                        >
                          Close & release unspent commitments
                        </button>
                      )}
                      <button
                        disabled={busy}
                        onClick={() => exportPlan(plan, "json")}
                      >
                        <Download size={15} /> JSON summary
                      </button>
                      <button
                        disabled={busy}
                        onClick={() => exportPlan(plan, "csv")}
                      >
                        <Download size={15} /> CSV summary
                      </button>
                    </div>
                  )}
                </Card>
              )}
              {planner && state.summary && (
                <Card title="Projected versus recorded outcomes">
                  <div className="funnel">
                    <div>
                      <span>Current projected additional</span>
                      <strong>{state.summary.projected_additional}</strong>
                    </div>
                    <div>
                      <span>Post-activation confirmed</span>
                      <strong>{state.summary.post_activation_confirmed}</strong>
                    </div>
                    <div>
                      <span>Post-activation completed</span>
                      <strong>{state.summary.post_activation_completed}</strong>
                    </div>
                  </div>
                  <p>
                    Activating resources does not complete requests. Operators
                    must still record confirmation, arrival and service
                    completion.
                  </p>
                </Card>
              )}
            </>
          )}
          <details className="audit-panel">
            <summary>Audit trail · {state.audit.length} recent events</summary>
            {state.audit
              .slice()
              .reverse()
              .map((a) => (
                <div key={a.id}>
                  <strong>{human(a.action)}</strong>
                  <span>
                    {a.actor} · {a.object_id}
                  </span>
                  <small>
                    {new Date(a.timestamp).toLocaleString("en-PK", {
                      timeZone: "Asia/Karachi",
                    })}{" "}
                    PKT {a.reason && `· ${a.reason}`}
                  </small>
                </div>
              ))}
          </details>
          <footer>
            SEHAT GRID · Scope v1.0 · Synthetic operational data · Geography is
            demonstration context, not a confirmed provider agreement.
          </footer>
        </main>
      </div>
    </div>
  );
  function MatchingTools() {
    return (
      <>
        <Form
          busy={busy}
          submit="Suggest matching records"
          fields={[
            {
              name: "kind",
              label: "Record type",
              options: [
                { value: "facility", label: "Facility identity" },
                { value: "service", label: "Primary-care service description" },
              ],
            },
            {
              name: "text",
              label: "Original text",
              value: "family doctor outpatient visit",
            },
            {
              name: "zone",
              label: "Locality evidence",
              options: [{ value: "", label: "Unknown" }, ...zones],
              required: false,
            },
          ]}
          onSubmit={(d) =>
            run(async () => {
              setMatchKind(d.kind as "facility" | "service");
              setMatch(
                await api<Match>(
                  `matching/${d.kind === "facility" ? "facilities" : "services"}`,
                  token,
                  "POST",
                  { text: d.text, zone: d.zone || null },
                ),
              );
            }, "Candidates are suggestions. A human decision is required.")
          }
        />
        {match && (
          <div className="matching">
            <Badge value={match.status} />
            <MatchDecisionTrace
              match={match}
              state={state!}
              reviews={state!.reviews}
            />
            <Form
              key={match.id}
              busy={busy}
              submit="Record review"
              fields={[
                {
                  name: "candidate_id",
                  label: "Canonical candidate",
                  options: [
                    { value: "", label: "No supported match" },
                    ...match.candidates.map((c) => ({
                      value: c.id,
                      label: `${facilityName(c.id, c.name)} · similarity ${c.score.toFixed(2)}`,
                    })),
                  ],
                  required: false,
                },
                {
                  name: "decision",
                  label: "Human decision",
                  options: [
                    { value: "ACCEPT", label: "Accept suggestion" },
                    { value: "CORRECT", label: "Correct category / identity" },
                    { value: "DECLINE", label: "Decline suggestion" },
                  ],
                },
                {
                  name: "record_id",
                  label:
                    matchKind === "facility"
                      ? "Original facility ID to link (planner only; optional)"
                      : "Existing request ID to review (optional)",
                  required: false,
                },
                {
                  name: "reason",
                  label: "Review reason",
                  value:
                    "Reviewed source text and supported primary-care scope",
                },
              ]}
              onSubmit={(d) =>
                run(() =>
                  mutate("matching/reviews", {
                    ...d,
                    match_id: match.id,
                    candidate_id: d.candidate_id || null,
                    record_id: d.record_id || null,
                  }),
                )
              }
            />
            <p>
              Identity links retain original records. No request, quota or
              reservation is moved by a match.
            </p>
          </div>
        )}
      </>
    );
  }
  function OfferForm({ kind }: { kind: "QUOTA" | "MOBILE" }) {
    return (
      <Form
        busy={busy}
        submit="Record dated offer"
        fields={[
          {
            name: "facility_id",
            label: "Responsible provider",
            options: facilityOptions,
          },
          {
            name: "date",
            label: "Operating date",
            type: "date",
            value: serviceDate,
          },
          { name: "zone", label: "Eligible pilot zone", options: zones },
          { name: "units", label: "Offered units", type: "number", value: 5 },
          {
            name: "cost",
            label: "Fixed package cost (PKR)",
            type: "number",
            value: 5000,
          },
          {
            name: "funding_included",
            label: "Package cost includes service funding",
            type: "checkbox",
            value: true,
          },
          ...(kind === "QUOTA"
            ? [
                {
                  name: "spare_group",
                  label: "Shared spare-capacity group",
                  value: "SPARE-NEW",
                },
              ]
            : [
                {
                  name: "mobile_unit",
                  label: "Mobile unit ID",
                  value: "MOBILE-02",
                },
                {
                  name: "site",
                  label: "Predeclared site name",
                  value: "Reviewed pilot site",
                },
              ]),
          { name: "latitude", label: "Site latitude", value: 33.746 },
          { name: "longitude", label: "Site longitude", value: 73.03 },
        ]}
        onSubmit={(d) =>
          run(() =>
            mutate(
              kind === "QUOTA" ? "partner-quota-offers" : "mobile-offers",
              {
                facility_id: d.facility_id,
                date: d.date,
                eligible_zones: [d.zone],
                units: Number(d.units),
                cost: Number(d.cost),
                funding_included: d.funding_included,
                spare_group: d.spare_group || null,
                mobile_unit: d.mobile_unit || null,
                site: d.site || null,
                latitude: Number(d.latitude),
                longitude: Number(d.longitude),
              },
            ),
          )
        }
      />
    );
  }
}
