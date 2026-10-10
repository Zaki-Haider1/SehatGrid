"use client";
import { useCallback, useEffect, useRef, useState, FormEvent } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Building2,
  Check,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  HeartPulse,
  LayoutDashboard,
  MapPin,
  Plus,
  RefreshCw,
  SlidersHorizontal,
  Sparkles,
  Wallet,
  X,
} from "lucide-react";
import {
  api,
  money,
  Service,
  Facility,
  CareRequest,
  Recommendation,
  Dashboard,
  Plan,
  Config,
} from "@/lib/api";
import { NetworkMap } from "@/components/network-map";
import { Dialog } from "@/components/dialog";
import { HospitalProfile } from "@/components/hospital-profile";

const tabs = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Providers", icon: Building2 },
  { name: "Referrals", icon: ClipboardList },
  { name: "Demand insights", icon: Activity },
  { name: "Resources", icon: Wallet },
];
type Modal = {
  type: "request" | "facility" | "capacity" | "recommend" | "reset";
  id?: number;
} | null;

export default function Home() {
  const [tab, setTab] = useState("Overview");
  const [view, setView] = useState("operator");
  const [config, setConfig] = useState<Config | null>(null);
  const [day, setDay] = useState("");
  const [services, setServices] = useState<Service[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [requests, setRequests] = useState<CareRequest[]>([]);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [modal, setModal] = useState<Modal>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [matches, setMatches] = useState<
    { service_id: number; name: string; score: number }[]
  >([]);
  const [serviceChoice, setServiceChoice] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [hospitalSearch, setHospitalSearch] = useState("");
  const [ownership, setOwnership] = useState("all");
  const refreshVersion = useRef(0);

  const refresh = useCallback(async (targetDay: string) => {
    const version = ++refreshVersion.current;
    const suffix = `?day=${targetDay}`;
    const [f, r, d, p] = await Promise.all([
      api<Facility[]>(`/api/facilities${suffix}`),
      api<CareRequest[]>(`/api/requests${suffix}`),
      api<Dashboard>(`/api/dashboard${suffix}`),
      api<Plan[]>(`/api/plans${suffix}`),
    ]);
    if (version !== refreshVersion.current) return;
    setFacilities(f);
    setRequests(r);
    setDashboard(d);
    setPlans(p);
    setSelected((current) =>
      f.some((provider) => provider.id === current)
        ? current
        : f[0]?.id || null,
    );
  }, []);

  useEffect(() => {
    let live = true;
    Promise.all([api<Config>("/api/config"), api<Service[]>("/api/services")])
      .then(([c, s]) => {
        if (live) {
          setConfig(c);
          setServices(s);
          setDay(c.today);
        }
      })
      .catch((e) => {
        if (live) {
          setError(
            `Cannot connect to the API. ${e.message}. Start the backend and refresh.`,
          );
          setLoading(false);
        }
      });
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => {
    if (!day) return;
    let live = true;
    setLoading(true);
    refresh(day)
      .catch((e) => {
        if (live) setError(e.message);
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [day, refresh]);

  async function act(work: () => Promise<void>, message = "") {
    if (busy || loading) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
      await refresh(day);
      if (message) setNotice(message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }
  async function showRecommendations(id: number) {
    await act(async () => {
      const options = await api<Recommendation[]>(
        `/api/requests/${id}/recommendations`,
      );
      setRecommendations(options);
      setModal({ type: "recommend", id });
    });
  }
  function openRequest() {
    setMatches([]);
    setServiceChoice(String(services[0]?.id || ""));
    setModal({ type: "request" });
  }
  function formValues(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    return Object.fromEntries(new FormData(event.currentTarget));
  }
  async function submitRequest(event: FormEvent<HTMLFormElement>) {
    const values = formValues(event);
    await act(async () => {
      const result = await api<{
        id: number;
        reference: string;
        recommendations: Recommendation[];
      }>("/api/requests", "POST", {
        service_id: Number(values.service_id),
        zone: values.zone,
        day,
        priority: values.priority,
      });
      setRecommendations(result.recommendations);
      setModal({ type: "recommend", id: result.id });
      setNotice(`${result.reference} added to the care queue`);
    });
  }
  async function exportData() {
    await act(async () => {
      const data = await api(`/api/export?day=${day}`);
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
      );
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `sehat-grid-${day}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    }, "Demo data exported");
  }
  const chosen = facilities.find((f) => f.id === selected);
  const queue = requests.filter((r) => filter === "all" || r.status === filter);
  const directory = facilities.filter(
    (f) =>
      (ownership === "all" || f.profile.ownership === ownership) &&
      `${f.name} ${f.profile.sector || ""} ${f.profile.address || ""}`
        .toLowerCase()
        .includes(hospitalSearch.trim().toLowerCase()),
  );
  const zoneSelect = (
    <select name="zone" defaultValue="Central">
      {config?.zones.map((z) => (
        <option key={z}>{z}</option>
      ))}
    </select>
  );
  const serviceSelect = (
    <select name="service_id">
      {services.map((s) => (
        <option key={s.id} value={s.id}>
          {s.name}
        </option>
      ))}
    </select>
  );

  function requestTable(limit?: number) {
    const rows = limit ? queue.slice(0, limit) : queue;
    return (
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Request / service</th>
              <th>Zone</th>
              <th>Provider</th>
              <th>Status</th>
              <th>
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>
                  <strong>{r.service_name}</strong>
                  <small>
                    {r.reference}
                    {r.priority === "urgent" && (
                      <span className="urgent"> · Urgent</span>
                    )}
                  </small>
                </td>
                <td>{r.zone}</td>
                <td>
                  {r.provider || (
                    <span className="muted">Awaiting provider</span>
                  )}
                </td>
                <td>
                  <span className={`badge ${r.status}`}>{r.status}</span>
                </td>
                <td className="row-actions">
                  {r.status === "pending" && (
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() => showRecommendations(r.id)}
                    >
                      Find provider <ArrowRight size={14} />
                    </button>
                  )}
                  {r.status === "reserved" && (
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() =>
                        act(async () => {
                          await api(
                            `/api/referrals/${r.referral_id}/confirm`,
                            "POST",
                          );
                        }, "Referral confirmed")
                      }
                    >
                      Confirm
                    </button>
                  )}
                  {r.status === "confirmed" && (
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() =>
                        act(async () => {
                          await api(
                            `/api/referrals/${r.referral_id}/complete`,
                            "POST",
                          );
                        }, "Care marked complete")
                      }
                    >
                      Complete
                    </button>
                  )}
                  {["reserved", "confirmed"].includes(r.status) && (
                    <button
                      title="Cancel referral and release slot"
                      aria-label={`Cancel ${r.reference}`}
                      className="icon-button subtle"
                      disabled={busy}
                      onClick={() =>
                        act(async () => {
                          await api(
                            `/api/referrals/${r.referral_id}/cancel`,
                            "POST",
                          );
                        }, "Slot released; request returned to queue")
                      }
                    >
                      <X size={14} />
                    </button>
                  )}
                  {r.status === "completed" && (
                    <Check size={16} className="green" />
                  )}
                </td>
              </tr>
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={5} className="empty">
                  No requests for this view. Add a request to begin.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    );
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a href="/" className="brand">
          <span className="brand-mark">
            <HeartPulse size={23} />
          </span>
          <span>
            sehat<span className="brand-light">grid</span>
            <small>CARE, CONNECTED</small>
          </span>
        </a>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {tabs.map(({ name, icon: Icon }) => (
            <button
              key={name}
              onClick={() => setTab(name)}
              className={tab === name ? "active" : ""}
            >
              <Icon size={18} />
              <span>{name}</span>
              {name === "Referrals" && !!dashboard?.pending && (
                <i>{dashboard.pending}</i>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="demo-card">
            <span className="dot indigo" />
            <strong>Demo workspace</strong>
            <p>Islamabad hospitals. Demo workflows.</p>
          </div>
          <div className="profile">
            <span className="avatar">SG</span>
            <div>
              <strong>
                {view === "operator" ? "Care operator" : "Resource planner"}
              </strong>
              <small>Sehat Grid team</small>
            </div>
            <CircleHelp size={17} />
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />
            <strong>{tab}</strong>
          </div>
          <div className="topbar-controls">
            <div className="view-switch">
              <button
                className={view === "operator" ? "selected" : ""}
                onClick={() => {
                  setView("operator");
                  setTab("Overview");
                }}
              >
                Operator
              </button>
              <button
                className={view === "planner" ? "selected" : ""}
                onClick={() => {
                  setView("planner");
                  setTab("Resources");
                }}
              >
                Planner
              </button>
            </div>
            <span className="topbar-divider" />
            <span className="avatar small">SG</span>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">YOUR CARE NETWORK</div>
              <h1>
                {tab === "Overview" ? "A healthier city starts here." : tab}
              </h1>
              <p>
                {tab === "Overview"
                  ? "Explore Islamabad’s hospitals and coordinate demo care."
                  : tab === "Providers"
                    ? "Sourced hospital details and simulated capacity."
                    : tab === "Referrals"
                      ? "Coordinate care, from request to completion."
                      : tab === "Demand insights"
                        ? "See where demand needs a little more support."
                        : "Put resources where they can make a difference."}
              </p>
            </div>
            <div className="heading-actions">
              <input
                aria-label="Dashboard date"
                type="date"
                value={day}
                onChange={(e) => {
                  if (e.target.value) setDay(e.target.value);
                }}
              />
              <button
                className="primary"
                disabled={busy || !config}
                onClick={openRequest}
              >
                <Plus size={17} />
                New request
              </button>
            </div>
          </div>
          {error && (
            <div role="alert" className="banner error">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div role="status" className="banner success">
              {notice}
              <button
                aria-label="Dismiss message"
                onClick={() => setNotice("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {loading && (
            <div className="loading-line" role="status">
              Connecting to your care network…
            </div>
          )}
          {dashboard && (
            <>
              <div className="stats">
                {[
                  {
                    label: "Network providers",
                    value: dashboard.facilities,
                    icon: Building2,
                    note: "Islamabad hospital directory",
                    tone: "blue",
                  },
                  {
                    label: "Demo slots available",
                    value: dashboard.available,
                    icon: HeartPulse,
                    note: "Simulated for workflow testing",
                    tone: "green",
                  },
                  {
                    label: "Active referrals",
                    value: dashboard.active_referrals,
                    icon: ClipboardList,
                    note: `${dashboard.completed} care journeys completed`,
                    tone: "purple",
                  },
                  {
                    label: "Unresolved requests",
                    value: dashboard.pending,
                    icon: Activity,
                    note: "Waiting for the right care",
                    tone: "orange",
                  },
                ].map(({ label, value, icon: Icon, note, tone }) => (
                  <div key={label} className="stat-card">
                    <div className="stat-label">
                      {label}
                      <span className={`stat-icon ${tone}`}>
                        <Icon size={18} />
                      </span>
                    </div>
                    <div className="stat-value">
                      {value.toString().padStart(2, "0")}
                    </div>
                    <small>{note}</small>
                  </div>
                ))}
              </div>

              {tab === "Overview" && (
                <>
                  <div className="overview-grid">
                    <section className="panel network-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>Your provider network</h2>
                          <p>
                            Real hospital locations · simulated care workflows
                          </p>
                        </div>
                        <span className="tag">
                          <MapPin size={13} />
                          Islamabad
                        </span>
                      </div>
                      <NetworkMap
                        facilities={facilities}
                        selected={selected}
                        onSelect={setSelected}
                      />
                    </section>
                    <section className="panel facility-detail">
                      <div className="panel-heading">
                        <h2>Provider snapshot</h2>
                        <SlidersHorizontal size={17} className="muted" />
                      </div>
                      <select
                        aria-label="Select provider"
                        value={selected || ""}
                        onChange={(e) => setSelected(Number(e.target.value))}
                      >
                        {facilities.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.name}
                          </option>
                        ))}
                      </select>
                      {chosen && (
                        <>
                          <div className="provider-meta">
                            <span className="provider-icon">
                              <Building2 size={24} />
                            </span>
                            <div>
                              <h3>{chosen.name}</h3>
                              <p>
                                {chosen.kind} ·{" "}
                                {chosen.profile.sector || chosen.zone}
                              </p>
                            </div>
                          </div>
                          <HospitalProfile facility={chosen} />
                          <p className="capacity-caption">
                            Demo capacity for {day}
                          </p>
                          <div className="capacity-list">
                            {chosen.capacities.map((c) => (
                              <div key={c.service_id}>
                                <span>
                                  {c.service_name}
                                  <small>
                                    {c.reserved} reserved · {c.consumed}{" "}
                                    completed
                                  </small>
                                </span>
                                <strong
                                  className={
                                    c.available ? "green" : "coral-text"
                                  }
                                >
                                  {c.available}
                                  <small>demo slots</small>
                                </strong>
                              </div>
                            ))}
                            {!chosen.capacities.length && (
                              <p className="muted">
                                No demo capacity reported. This does not mean
                                the hospital is full or lacks services.
                              </p>
                            )}
                          </div>
                          <button
                            className="secondary full"
                            disabled={busy}
                            onClick={() =>
                              setModal({ type: "capacity", id: chosen.id })
                            }
                          >
                            <Plus size={16} />
                            Update demo capacity
                          </button>
                        </>
                      )}
                    </section>
                  </div>
                  <section className="panel queue-panel">
                    <div className="panel-heading">
                      <div>
                        <h2>
                          Care queue{" "}
                          <span className="count">{requests.length}</span>
                        </h2>
                        <p>The next step in every care journey</p>
                      </div>
                      <button
                        className="text-button"
                        onClick={() => setTab("Referrals")}
                      >
                        View all <ArrowRight size={15} />
                      </button>
                    </div>
                    {requestTable(5)}
                  </section>
                </>
              )}

              {tab === "Providers" && (
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Provider directory</h2>
                      <p>
                        {directory.length} hospitals shown · demo capacity for{" "}
                        {day}
                      </p>
                    </div>
                    <button
                      className="secondary"
                      onClick={() => setModal({ type: "facility" })}
                    >
                      <Plus size={16} />
                      Register provider
                    </button>
                  </div>
                  <div className="directory-controls">
                    <input
                      aria-label="Search hospitals"
                      placeholder="Search hospital, sector or address"
                      value={hospitalSearch}
                      onChange={(e) => setHospitalSearch(e.target.value)}
                    />
                    <select
                      aria-label="Hospital ownership"
                      value={ownership}
                      onChange={(e) => setOwnership(e.target.value)}
                    >
                      <option value="all">Public &amp; private</option>
                      <option value="Public">Public hospitals</option>
                      <option value="Private">Private hospitals</option>
                    </select>
                  </div>
                  <div className="provider-grid">
                    {directory.map((f) => (
                      <article className="provider-card" key={f.id}>
                        <span className="provider-icon">
                          <Building2 size={24} />
                        </span>
                        <h3>{f.name}</h3>
                        <p>
                          {f.kind} · {f.profile.sector || f.zone}
                        </p>
                        <HospitalProfile facility={f} />
                        <button
                          className="text-button locate-hospital"
                          onClick={() => {
                            setSelected(f.id);
                            setTab("Overview");
                          }}
                        >
                          Locate on map <MapPin size={13} />
                        </button>
                        <p className="capacity-caption">
                          Demo capacity · {f.zone} planning catchment
                        </p>
                        <div className="provider-capacity">
                          {f.capacities.map((c) => (
                            <div key={c.service_id}>
                              <span>{c.service_name}</span>
                              <strong>
                                {c.available}
                                <small> / {c.total}</small>
                              </strong>
                            </div>
                          ))}
                          {!f.capacities.length && (
                            <p>No demo capacity reported for this date</p>
                          )}
                        </div>
                        <button
                          className="secondary full"
                          onClick={() =>
                            setModal({ type: "capacity", id: f.id })
                          }
                        >
                          Update demo capacity <ArrowRight size={15} />
                        </button>
                      </article>
                    ))}
                    {!directory.length && (
                      <p className="empty">No hospitals match your search.</p>
                    )}
                  </div>
                </section>
              )}

              {tab === "Referrals" && (
                <section className="panel">
                  <div className="panel-heading">
                    <h2>Referral workspace</h2>
                    <select
                      aria-label="Filter referrals"
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                    >
                      {[
                        "all",
                        "pending",
                        "reserved",
                        "confirmed",
                        "completed",
                      ].map((s) => (
                        <option key={s} value={s}>
                          {s === "all"
                            ? "All statuses"
                            : s.charAt(0).toUpperCase() + s.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                  {requestTable()}
                </section>
              )}

              {tab === "Demand insights" && (
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Unmet demand by zone</h2>
                      <p>Live signals from unresolved requests</p>
                    </div>
                    <button
                      className="secondary"
                      onClick={() => setTab("Resources")}
                    >
                      Plan resources <ArrowRight size={16} />
                    </button>
                  </div>
                  <div className="insight-list">
                    {dashboard.gaps.map((g) => (
                      <div
                        className="insight-row"
                        key={`${g.zone}-${g.service}`}
                      >
                        <span className="zone-icon">
                          <MapPin size={20} />
                        </span>
                        <div>
                          <h3>{g.zone}</h3>
                          <p>{g.service}</p>
                        </div>
                        <span className="badge pending">{g.reason}</span>
                        <div className="insight-count">
                          <strong>{g.pending}</strong>
                          <small>pending</small>
                        </div>
                      </div>
                    ))}
                    {!dashboard.gaps.length && (
                      <p className="empty">
                        All care requests have a next step. No unresolved
                        demand.
                      </p>
                    )}
                  </div>
                </section>
              )}

              {tab === "Resources" && (
                <div className="resource-grid">
                  <section className="panel">
                    <div className="panel-heading">
                      <div>
                        <h2>Fund the next care journey</h2>
                        <p>
                          Optimize additional slots against unresolved local
                          demand
                        </p>
                      </div>
                      <Sparkles size={19} className="indigo-text" />
                    </div>
                    <div className="budget-balance">
                      <small>AVAILABLE BUDGET</small>
                      <h2>
                        <span>PKR</span> {money(dashboard.budget.remaining)}
                      </h2>
                      <p>
                        PKR {money(dashboard.budget.committed)} committed of{" "}
                        {money(dashboard.budget.total)}
                      </p>
                    </div>
                    <form
                      className="resource-form"
                      onSubmit={(e) => {
                        const v = formValues(e);
                        act(async () => {
                          await api("/api/budget", "PUT", {
                            total: Number(v.total),
                          });
                        }, "Budget updated");
                      }}
                    >
                      <label>
                        Total budget (PKR)
                        <input
                          name="total"
                          type="number"
                          min={dashboard.budget.committed}
                          max="100000000"
                          required
                          defaultValue={dashboard.budget.total}
                          key={dashboard.budget.total}
                        />
                      </label>
                      <button className="secondary" disabled={busy}>
                        Save budget
                      </button>
                    </form>
                    <form
                      className="resource-form"
                      onSubmit={(e) => {
                        const v = formValues(e);
                        act(async () => {
                          await api("/api/plans", "POST", {
                            day,
                            limit: Number(v.limit),
                          });
                        }, "Allocation plan ready for review");
                      }}
                    >
                      <label>
                        Spend limit for this plan (PKR)
                        <input
                          name="limit"
                          type="number"
                          min="1"
                          max="100000000"
                          required
                          defaultValue={Math.max(1, dashboard.budget.remaining)}
                          key={dashboard.budget.remaining}
                        />
                      </label>
                      <button
                        className="primary"
                        disabled={busy || !dashboard.budget.remaining}
                      >
                        <Sparkles size={16} />
                        Generate plan
                      </button>
                    </form>
                    <p className="form-note">
                      Urgent demand first, then the most care slots within
                      budget. Approval activates capacity and retries pending
                      requests.
                    </p>
                  </section>
                  <section className="panel">
                    <div className="panel-heading">
                      <h2>Allocation plans</h2>
                      <span className="count">{plans.length}</span>
                    </div>
                    <div className="plan-list">
                      {plans.map((p) => (
                        <article className="plan-card" key={p.id}>
                          <div className="plan-top">
                            <h3>Plan #{p.id}</h3>
                            <span className={`badge ${p.status}`}>
                              {p.status}
                            </span>
                          </div>
                          <div className="plan-numbers">
                            <strong>
                              {p.units} <small>new slots</small>
                            </strong>
                            <strong>PKR {money(p.cost)}</strong>
                          </div>
                          {p.allocations.map((a, i) => (
                            <p className="allocation" key={i}>
                              <span>
                                {a.service_name}
                                <small>
                                  {a.facility_name} · {a.zone}
                                </small>
                              </span>
                              <b>+{a.units}</b>
                            </p>
                          ))}
                          {!p.units && (
                            <p className="muted">
                              No additional slots can be funded for this demand
                              and limit.
                            </p>
                          )}
                          {p.status === "draft" && p.units > 0 && (
                            <button
                              className="primary full"
                              disabled={busy}
                              onClick={() =>
                                act(async () => {
                                  const r = await api<{ reprocessed: number }>(
                                    `/api/plans/${p.id}/approve`,
                                    "POST",
                                  );
                                  setNotice(
                                    `Plan approved. ${r.reprocessed} requests reserved with providers.`,
                                  );
                                })
                              }
                            >
                              Approve & activate <ArrowRight size={16} />
                            </button>
                          )}
                        </article>
                      ))}
                      {!plans.length && (
                        <div className="empty">
                          <Wallet size={30} />
                          <p>Your first plan starts with a budget.</p>
                        </div>
                      )}
                    </div>
                  </section>
                </div>
              )}

              <footer>
                <span>
                  <i className="dot green-dot" />
                  Real directory · simulated capacity · {day}
                </span>
                <div>
                  <button
                    disabled={busy}
                    onClick={() => act(async () => {}, "Network refreshed")}
                  >
                    <RefreshCw size={13} />
                    Refresh
                  </button>
                  <button disabled={busy} onClick={exportData}>
                    <ArrowDownToLine size={14} />
                    Export
                  </button>
                  {config?.demo_reset_enabled && (
                    <button
                      disabled={busy}
                      onClick={() => setModal({ type: "reset" })}
                    >
                      Reset demo
                    </button>
                  )}
                </div>
              </footer>
            </>
          )}
        </main>
      </div>

      {modal && (
        <Dialog
          title={
            modal.type === "request"
              ? "New care request"
              : modal.type === "facility"
                ? "Register provider"
                : modal.type === "capacity"
                  ? "Update service capacity"
                  : modal.type === "reset"
                    ? "Reset demo workspace"
                    : "Choose a care provider"
          }
          close={() => {
            if (!busy) setModal(null);
          }}
        >
          {modal.type === "request" && (
            <form onSubmit={submitRequest} className="dialog-form">
              <p className="form-note">
                Create a synthetic request for {day}. Choose the service after
                reviewing any suggestions.
              </p>
              <label>
                Describe the service (optional)
                <div className="input-action">
                  <input
                    id="service-description"
                    placeholder="e.g. blood test or kidney treatment"
                  />
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      act(async () => {
                        const input = document.getElementById(
                          "service-description",
                        ) as HTMLInputElement;
                        setMatches(
                          await api("/api/services/match", "POST", {
                            description: input.value,
                          }),
                        );
                      })
                    }
                  >
                    Suggest
                  </button>
                </div>
              </label>
              {matches.length > 0 && (
                <div className="match-list">
                  {matches.map((m) => (
                    <button
                      key={m.service_id}
                      type="button"
                      onClick={() => setServiceChoice(String(m.service_id))}
                    >
                      {m.name}
                      <span>{m.score}% text match</span>
                    </button>
                  ))}
                  <small>
                    Suggestions require your review; scores are text similarity.
                  </small>
                </div>
              )}
              <label>
                Service
                <select
                  name="service_id"
                  value={serviceChoice}
                  onChange={(e) => setServiceChoice(e.target.value)}
                >
                  {services.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="form-grid">
                <label>Request zone{zoneSelect}</label>
                <label>
                  Priority
                  <select name="priority">
                    <option value="routine">Routine</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </label>
              </div>
              <button className="primary full" disabled={busy}>
                Create request <ArrowRight size={16} />
              </button>
            </form>
          )}
          {modal.type === "facility" && (
            <form
              className="dialog-form"
              onSubmit={(e) => {
                const v = formValues(e);
                act(async () => {
                  await api("/api/facilities", "POST", {
                    ...v,
                    latitude: Number(v.latitude),
                    longitude: Number(v.longitude),
                  });
                  setModal(null);
                }, "Provider registered. Add service capacity to receive referrals.");
              }}
            >
              <label>
                Provider name
                <input
                  name="name"
                  required
                  minLength={3}
                  maxLength={120}
                  placeholder="e.g. City Care Clinic"
                />
              </label>
              <div className="form-grid">
                <label>Zone{zoneSelect}</label>
                <label>
                  Provider type
                  <select name="kind">
                    {[
                      "Hospital",
                      "Clinic",
                      "Diagnostic center",
                      "Community center",
                    ].map((k) => (
                      <option key={k}>{k}</option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="form-grid">
                <label>
                  Latitude
                  <input
                    name="latitude"
                    type="number"
                    step="any"
                    min="-90"
                    max="90"
                    placeholder="e.g. 33.702269"
                    required
                  />
                </label>
                <label>
                  Longitude
                  <input
                    name="longitude"
                    type="number"
                    step="any"
                    min="-180"
                    max="180"
                    placeholder="e.g. 73.052529"
                    required
                  />
                </label>
              </div>
              <button className="primary full" disabled={busy}>
                Register provider
              </button>
            </form>
          )}
          {modal.type === "capacity" && (
            <form
              className="dialog-form"
              onSubmit={(e) => {
                const v = formValues(e);
                act(async () => {
                  await api(`/api/facilities/${modal.id}/capacity`, "PUT", {
                    service_id: Number(v.service_id),
                    total: Number(v.total),
                    day,
                  });
                  setModal(null);
                }, "Provider capacity updated");
              }}
            >
              <p className="form-note">
                {facilities.find((f) => f.id === modal.id)?.name} · {day}
              </p>
              <label>Service{serviceSelect}</label>
              <label>
                Total service slots
                <input
                  name="total"
                  type="number"
                  min="0"
                  max="10000"
                  required
                  placeholder="Enter daily total"
                />
              </label>
              <p className="form-note">
                Total includes available, reserved, and completed slots.
              </p>
              <button className="primary full" disabled={busy}>
                Save capacity
              </button>
            </form>
          )}
          {modal.type === "recommend" && (
            <div className="dialog-form">
              <p className="form-note">
                Local providers are listed first. A slot is reserved only after
                you choose a provider.
              </p>
              {recommendations.map((r) => (
                <button
                  key={r.facility_id}
                  className="recommendation"
                  disabled={busy}
                  onClick={() =>
                    act(async () => {
                      await api(`/api/requests/${modal.id}/reserve`, "POST", {
                        facility_id: r.facility_id,
                      });
                      setModal(null);
                    }, "Slot reserved. Confirm the referral with the provider.")
                  }
                >
                  <span className="provider-icon">
                    <Building2 size={21} />
                  </span>
                  <span>
                    <strong>{r.name}</strong>
                    <small>
                      {r.zone} · {r.available} slots available{" "}
                      {r.local ? "· Local provider" : ""}
                    </small>
                  </span>
                  <ArrowRight size={17} />
                </button>
              ))}
              {!recommendations.length && (
                <div className="empty">
                  <HeartPulse size={30} />
                  <p>No slots available for this service and date.</p>
                  <small>
                    The request stays in unmet demand. A planner can fund
                    additional capacity.
                  </small>
                  <button
                    className="secondary"
                    onClick={() => {
                      setModal(null);
                      setView("planner");
                      setTab("Resources");
                    }}
                  >
                    Open resources
                  </button>
                </div>
              )}
            </div>
          )}
          {modal.type === "reset" && (
            <div className="dialog-form">
              <p>
                Reset removes all demo requests, capacity changes, and plans,
                then restores the synthetic dataset.
              </p>
              <button
                className="primary full"
                disabled={busy}
                onClick={() =>
                  act(async () => {
                    await api(
                      "/api/demo/reset?confirm=RESET_SYNTHETIC_DATA",
                      "POST",
                    );
                    setModal(null);
                    setDay(config?.today || day);
                  }, "Demo restored")
                }
              >
                Reset synthetic data
              </button>
            </div>
          )}
          {busy && (
            <p className="dialog-status" role="status">
              Saving changes…
            </p>
          )}
          {error && (
            <p className="dialog-error" role="alert">
              {error}
            </p>
          )}
        </Dialog>
      )}
    </div>
  );
}
