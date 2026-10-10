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
  API,
  human,
  money,
  State,
  User,
  Facility,
  CareRequest,
  Recommendation,
  RecommendationResult,
  Match,
  Plan,
} from "@/lib/api";
import { PilotMap } from "@/components/pilot-map";
import { Dialog } from "@/components/dialog";
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
  }
  useEffect(() => {
    if (token)
      load().catch((e) => {
        setError(e.message);
        if (e.message.includes("Sign in")) {
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
        data,
      );
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
    setMatch(null);
    setRequest(null);
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
            Connect available care.
            <br />
            Make every resource count.
          </h1>
          <p>
            A shared workspace for hospital operators and network planners.
            Coordinate reviewed referrals, see unresolved requests, and put a
            monthly resource plan into action.
          </p>
          <div className="login-pills">
            <span>01 Hospital network</span>
            <span>02 Referral coordination</span>
            <span>03 Network intelligence</span>
            <span>04 Monthly allocation</span>
          </div>
          <small>
            Synthetic demonstration · no patient login · no real payments
          </small>
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
            <p>Loading your workspace…</p>
          ) : (
            <Form
              busy={busy}
              onSubmit={login}
              submit="Sign in"
              fields={[
                {
                  name: "username",
                  label: "Account",
                  value: "planner",
                  options: [
                    { value: "planner", label: "Network planner" },
                    ...Array.from({ length: 8 }, (_, i) => ({
                      value: `operator-p0${i + 1}`,
                      label: `P0${i + 1} hospital operator`,
                    })),
                  ],
                },
                { name: "password", label: "Demo password", type: "password" },
              ]}
            />
          )}
          <small>Use the password configured for this deployment.</small>
        </div>
      </main>
    );
  const planner = state.user.role === "planner",
    own = state.facilities.filter((f) =>
      state.user.facility_ids.includes(f.id),
    ),
    facility =
      state.facilities.find((f) => f.id === selected) ||
      own[0] ||
      state.facilities[0],
    serviceDate = day || state.config.service_date,
    planningMonth = month || state.config.month;
  const zones = state.config.zones.map((z) => ({ value: z.id, label: z.name })),
    facilityOptions = own.map((f) => ({ value: f.id, label: f.name }));
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
    { name: "name", label: "Demo provider name", value: f?.name },
    {
      name: "ownership",
      label: "Ownership",
      value: f?.ownership,
      options: [
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
    <div className="app">
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
          <span>{state.user.name}</span>
          <Badge value={state.user.role} />
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
          <i /> Synthetic demo data
        </span>
        <span>
          Non-emergency primary-care only · reported network quota, not hospital
          workload
        </span>
      </div>
      <div className="workspace">
        <aside className="sidebar">
          <span className="nav-label">WORKSPACE</span>
          {[
            {
              id: "network",
              name: planner ? "Network overview" : "Facility dashboard",
              icon: Network,
            },
            {
              id: "referrals",
              name: planner ? "Funding approvals" : "Referral coordination",
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
          ].map((item) => (
            <button
              key={item.id}
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
                {planner ? "NETWORK PLANNER" : "HOSPITAL OPERATOR"}
              </span>
              <h1>
                {screen === "network"
                  ? "Care, connected."
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
                  ? "A current view of your participating primary-care network."
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
          {screen === "network" && (
            <>
              <div className="network-layout">
                <Card
                  title="Participating providers"
                  aside={
                    <span className="count">{state.facilities.length}</span>
                  }
                >
                  <div className="provider-list">
                    {state.facilities.map((f) => (
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
                          <strong>{f.name}</strong>
                          <span>
                            {f.zone} · {f.ownership}
                          </span>
                          <small>
                            {f.directory_context?.name ||
                              "New demonstration provider"}
                          </small>
                        </div>
                        <Badge value={f.capacities[0]?.status || "UNKNOWN"} />
                      </button>
                    ))}
                  </div>
                </Card>
                <PilotMap
                  state={state}
                  selected={selected}
                  onSelect={setSelected}
                />
              </div>
              {facility && (
                <Card
                  title={facility.name}
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
              {!planner && (
                <div className="two-col">
                  <Card title="Register a demonstration provider">
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
                      <details key={f.id}>
                        <summary>{f.name}</summary>
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
              {!planner && (
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
                              ? `Accept suggestion: ${c.name}`
                              : `Correct to: ${c.name}`}
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
                          label: "Synthetic reference",
                          value: `DEMO-${state.requests.length + 1}`,
                        },
                        {
                          name: "source_facility_id",
                          label: "Originating provider",
                          options: facilityOptions,
                        },
                        { name: "zone", label: "Pilot zone", options: zones },
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
                      onSubmit={(d) =>
                        run(() =>
                          mutate("requests", {
                            ...d,
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
                      <div key={o.capacity_id} className="recommendation">
                        <strong>{o.name}</strong>
                        <p>{o.explanation}</p>
                        <span>
                          {o.date} · {o.available} units · Subsidy PKR{" "}
                          {money(o.subsidy)}
                        </span>
                        <button
                          className="primary"
                          disabled={busy}
                          onClick={() =>
                            run(async () => {
                              await mutate("referrals", {
                                request_id: request!.id,
                                capacity_id: o.capacity_id,
                                capacity_version: o.capacity_version,
                                facility_version: o.facility_version,
                              });
                              setOptions([]);
                              setReasons([]);
                              setRecommendationResult(null);
                            }, "Temporary hold created. Partner acceptance and patient agreement are pending.")
                          }
                        >
                          Approve & reserve
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
                          <tr key={r.id}>
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
                              {state.user.facility_ids.includes(
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
                      return (
                        <div className="referral" key={a.id}>
                          <div>
                            <strong>
                              {a.id} → {a.facility_id}
                            </strong>
                            <p>
                              {a.request_id} · {a.date} · Subsidy PKR{" "}
                              {money(a.subsidy)}
                            </p>
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
                                {new Date(a.expires_at).toLocaleString(
                                  "en-PK",
                                  { timeZone: "Asia/Karachi" },
                                )}{" "}
                                PKT
                              </small>
                            )}
                            {a.reason && <small>{a.reason}</small>}
                          </div>
                          <div className="action-buttons">
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
                            {o.facility_id}
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
                      <span>Original solver result</span>
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
                        <button
                          className="primary"
                          disabled={busy}
                          onClick={() =>
                            run(
                              () => mutate(`plans/${plan.id}/approve`),
                              "Plan approved. Funds and offers reserved; partner/mobile actions await their operators.",
                            )
                          }
                        >
                          Approve plan
                        </button>
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
                      label: `${c.name} · similarity ${c.score.toFixed(2)}`,
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
