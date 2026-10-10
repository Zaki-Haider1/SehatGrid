"use client";
import { useState } from "react";
import {
  ArrowUpRight,
  Building2,
  ChevronRight,
  Search,
  SlidersHorizontal,
  X,
  MapPin,
  Wallet,
  Activity,
} from "lucide-react";
import { PilotMap, hospitalColor, type MapLayer } from "./pilot-map";
import {
  money,
  human,
  hospitalName,
  hospitalShortName,
  type State,
} from "@/lib/api";
export function GovernmentOverview({
  state,
  selected,
  onSelect,
  navigate,
  previousMonth,
}: {
  state: State;
  selected: string | null;
  onSelect: (id: string | null) => void;
  navigate: (screen: string) => void;
  previousMonth: () => void;
}) {
  const [query, setQuery] = useState(""),
    [layer, setLayer] = useState<MapLayer>("capacity"),
    [filter, setFilter] = useState("all");
  const summary = state.summary!,
    f = state.facilities.find((f) => f.id === selected),
    budget = summary.budget;
  const facilities = state.facilities.filter(
    (f) =>
      `${f.name} ${f.directory_context?.name} ${f.zone}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (filter === "all" || f.capacities[0]?.status === filter),
  );
  const completedPlan = state.plans
    .filter(
      (p) =>
        p.month === summary.month &&
        ["APPROVED", "ACTIVE", "CLOSED"].includes(p.status),
    )
    .at(-1);
  return (
    <div className="government-city">
      <PilotMap
        state={state}
        selected={selected}
        onSelect={onSelect}
        layer={layer}
      />
      <aside className="city-directory floating-panel">
        <div className="directory-heading">
          <div>
            <span className="eyebrow">YOUR CARE NETWORK</span>
            <h2>
              Islamabad hospitals<span>{state.facilities.length}</span>
            </h2>
          </div>
          <span className="city-area">ICT</span>
        </div>
        <p className="subtle">Every hospital. One connected view.</p>
        <label className="city-search">
          <Search size={16} />
          <input
            aria-label="Search hospitals"
            placeholder="Find a hospital or area"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <div className="directory-filter">
          <SlidersHorizontal size={14} />
          <select
            aria-label="Filter hospitals"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All hospitals</option>
            <option value="AVAILABLE">Available capacity</option>
            <option value="LIMITED">Limited capacity</option>
            <option value="EXHAUSTED">Quota exhausted</option>
            <option value="UNKNOWN">Capacity unknown</option>
          </select>
          <span>{facilities.length} results</span>
        </div>
        <div className="city-hospital-list">
          {facilities.map((f) => (
            <button
              key={f.id}
              onClick={() => onSelect(f.id)}
              className={`city-hospital ${selected === f.id ? "active" : ""}`}
            >
              <div
                className="hospital-cube"
                style={
                  {
                    "--cube-color": hospitalColor(state, f.id, layer),
                  } as React.CSSProperties
                }
              >
                <Building2 size={20} />
              </div>
              <div>
                <strong>{hospitalName(f)}</strong>
                <span>
                  {f.zone} · {f.ownership}
                </span>
                <small>
                  {f.capacities[0]?.available ?? "Unknown"} slots available{" "}
                  <i
                    style={{
                      background: hospitalColor(state, f.id, "capacity"),
                    }}
                  />
                </small>
              </div>
              <ChevronRight size={15} />
            </button>
          ))}
          {!facilities.length && (
            <p className="empty">
              No hospitals match. Try another name or filter.
            </p>
          )}
        </div>
        <div className="directory-footer">
          <span className="live-dot" />
          Reported capacity · {state.config.service_date}
          <small>Public hospital locations; synthetic pilot operations.</small>
        </div>
      </aside>
      <div className="city-layer floating-panel">
        <span>Map view</span>
        <div>
          {(["capacity", "demand", "funding"] as MapLayer[]).map((v) => (
            <button
              key={v}
              className={layer === v ? "active" : ""}
              onClick={() => setLayer(v)}
            >
              {v === "capacity"
                ? "Capacity"
                : v === "demand"
                  ? "Unmet demand"
                  : "Funding"}
            </button>
          ))}
        </div>
      </div>
      {f ? (
        <aside className="city-detail floating-panel">
          <button
            className="detail-close icon-button"
            aria-label="Close hospital details"
            onClick={() => onSelect(null)}
          >
            <X size={16} />
          </button>
          <div className="detail-illustration">
            <div
              className="detail-building"
              style={
                {
                  "--cube-color": hospitalColor(state, f.id, layer),
                } as React.CSSProperties
              }
            >
              <Building2 size={40} />
            </div>
            <span>{hospitalShortName(f)}</span>
          </div>
          <span className="eyebrow">HOSPITAL OVERVIEW</span>
          <h2>{hospitalName(f)}</h2>
          <p className="subtle">
            <MapPin size={12} />
            {f.zone} · {f.ownership}
          </p>
          <span className={`badge ${f.participation.toLowerCase()}`}>
            {human(f.participation)}
          </span>
          <div className="detail-metrics">
            <div>
              <strong>{f.capacities[0]?.available ?? "—"}</strong>
              <span>Available slots</span>
            </div>
            <div>
              <strong>{f.capacities[0]?.quota ?? "—"}</strong>
              <span>Daily quota</span>
            </div>
          </div>
          <div className="capacity-track">
            <i
              style={{
                width: `${Math.min(100, Math.max(0, ((f.capacities[0]?.available || 0) / (f.capacities[0]?.quota || 1)) * 100))}%`,
                background: hospitalColor(state, f.id, "capacity"),
              }}
            />
          </div>
          <dl className="hospital-facts">
            <div>
              <dt>Capacity status</dt>
              <dd>{human(f.capacities[0]?.status || "UNKNOWN")}</dd>
            </div>
            <div>
              <dt>Funding support</dt>
              <dd>
                {f.subsidy_required
                  ? "Subsidy required"
                  : "No subsidy required"}
              </dd>
            </div>
            <div>
              <dt>Held / committed</dt>
              <dd>
                {f.capacities[0]?.held || 0} / {f.capacities[0]?.committed || 0}
              </dd>
            </div>
            <div>
              <dt>Completed</dt>
              <dd>{f.capacities[0]?.completed || 0}</dd>
            </div>
            <div>
              <dt>Eligible areas</dt>
              <dd>{f.eligible_zones.join(", ") || "None declared"}</dd>
            </div>
          </dl>
          <p className="detail-address">{f.address}</p>
          {!!f.catalog?.length && (
            <details>
              <summary>Services & prices ({f.catalog.length})</summary>
              {f.catalog.map((c) => (
                <div key={c.id} className="catalog-price">
                  <div>
                    {c.name}
                    <small>
                      {c.daily_capacity} / day ·{" "}
                      {c.active ? "Available" : "Unavailable"}
                    </small>
                  </div>
                  <strong>PKR {money(c.price)}</strong>
                </div>
              ))}
            </details>
          )}
          <button className="primary" onClick={() => navigate("providers")}>
            Manage participation
            <ArrowUpRight size={15} />
          </button>
        </aside>
      ) : (
        <aside className="city-insight floating-panel">
          <span className="eyebrow">MONTHLY PULSE · {summary.month}</span>
          <h2>Care within reach.</h2>
          <p>
            {summary.unresolved
              ? `${summary.unresolved} requests still need a route to care.`
              : "No unresolved requests recorded for this month."}
          </p>
          <div className="pulse-numbers">
            <div>
              <strong>{summary.confirmed}</strong>
              <span>Confirmed</span>
            </div>
            <div>
              <strong>{summary.completed}</strong>
              <span>Completed</span>
            </div>
          </div>
          <div className="pulse-plan">
            <Activity size={16} />
            <div>
              <strong>
                {completedPlan
                  ? `${summary.projected_additional} planned additional services`
                  : "No approved plan this month"}
              </strong>
              <small>
                {summary.post_activation_completed} completed after activation
              </small>
            </div>
          </div>
          <button className="text-button" onClick={previousMonth}>
            Review previous month
            <ArrowUpRight size={14} />
          </button>
        </aside>
      )}
      <div className="city-budget floating-panel">
        <div className="budget-icon">
          <Wallet size={20} />
        </div>
        <div>
          <span>Monthly budget</span>
          <strong>PKR {money(budget?.authorized || 0)}</strong>
        </div>
        <div className="budget-remaining">
          <span>Available to allocate</span>
          <strong>PKR {money(budget?.remaining || 0)}</strong>
        </div>
        <button onClick={() => navigate("planning")}>
          Plan resources
          <ArrowUpRight size={15} />
        </button>
      </div>
      <div className="city-legend floating-panel">
        {layer === "capacity" ? (
          <>
            <span>
              <i style={{ background: "#7397f6" }} />
              Available
            </span>
            <span>
              <i style={{ background: "#e7bd83" }} />
              Limited
            </span>
            <span>
              <i style={{ background: "#e68c92" }} />
              Exhausted
            </span>
            <span>
              <i style={{ background: "#b9c1ce" }} />
              Unknown
            </span>
          </>
        ) : (
          <>
            <span>
              <i style={{ background: "#e68c92" }} />
              {layer === "demand"
                ? "Unresolved demand in area"
                : "Subsidy required"}
            </span>
            <span>
              <i style={{ background: "#7397f6" }} />
              {layer === "demand"
                ? "No unresolved demand"
                : "No subsidy required"}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
