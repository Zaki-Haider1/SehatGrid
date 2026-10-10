"use client";
import { useState } from "react";
import { Plus, Pencil, Trash2, FlaskConical } from "lucide-react";
import { money, type CatalogItem, type Facility } from "@/lib/api";
export function HospitalCatalog({
  facility,
  save,
  busy,
}: {
  facility: Facility;
  save: (path: string, body: unknown, method: string) => Promise<void>;
  busy: boolean;
}) {
  const [editing, setEditing] = useState<CatalogItem | null>(null),
    [open, setOpen] = useState(false);
  return (
    <section className="card catalog-card">
      <div className="card-title">
        <div>
          <span className="eyebrow">SERVICES & TARIFFS</span>
          <h2>Hospital service catalog</h2>
        </div>
        <button
          className="primary"
          onClick={() => {
            setEditing(null);
            setOpen(true);
          }}
        >
          <Plus size={15} />
          Add service or test
        </button>
      </div>
      <p className="subtle">
        Set your hospital’s consultation, laboratory and imaging prices, and
        daily service capacity.
      </p>
      {open && (
        <form
          key={editing?.id || "new"}
          className="catalog-form"
          onSubmit={async (e) => {
            e.preventDefault();
            const data = new FormData(e.currentTarget);
            const body = {
              name: String(data.get("name")),
              category: String(data.get("category")),
              price: Number(data.get("price")),
              daily_capacity: Number(data.get("daily_capacity")),
              active: data.has("active"),
              version: facility.version,
            };
            try {
              await save(
                `facilities/${facility.id}/catalog${editing ? `/${editing.id}` : ""}`,
                body,
                editing ? "PATCH" : "POST",
              );
              setOpen(false);
            } catch {
              /* The workspace displays the API error; keep this draft open. */
            }
          }}
        >
          <div className="fields">
            <label>
              <span>Service or test name</span>
              <input
                name="name"
                required
                minLength={2}
                maxLength={120}
                defaultValue={editing?.name}
                placeholder="e.g. Complete blood count"
              />
            </label>
            <label>
              <span>Category</span>
              <select
                name="category"
                defaultValue={editing?.category || "Laboratory"}
              >
                {["Consultation", "Laboratory", "Imaging", "Other"].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Price (PKR)</span>
              <input
                type="number"
                name="price"
                required
                min="0"
                max="10000000"
                defaultValue={editing?.price ?? 0}
              />
            </label>
            <label>
              <span>Daily service capacity</span>
              <input
                type="number"
                name="daily_capacity"
                required
                min="0"
                max="10000"
                defaultValue={editing?.daily_capacity ?? 0}
              />
            </label>
            <label className="check-field">
              <input
                type="checkbox"
                name="active"
                defaultChecked={editing?.active ?? true}
              />
              <span>Service is available</span>
            </label>
          </div>
          <div className="action-buttons">
            <button className="primary" disabled={busy}>
              {editing ? "Save service changes" : "Add to catalog"}
            </button>
            <button type="button" onClick={() => setOpen(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}
      {facility.catalog?.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Service / test</th>
                <th>Category</th>
                <th>Price</th>
                <th>Daily capacity</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {facility.catalog.map((c) => (
                <tr key={c.id}>
                  <td>
                    <strong>{c.name}</strong>
                  </td>
                  <td>{c.category}</td>
                  <td>PKR {money(c.price)}</td>
                  <td>{c.daily_capacity}</td>
                  <td>
                    <span
                      className={`badge ${c.active ? "active" : "suspended"}`}
                    >
                      {c.active ? "Available" : "Unavailable"}
                    </span>
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button
                        aria-label={`Edit ${c.name}`}
                        onClick={() => {
                          setEditing(c);
                          setOpen(true);
                        }}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        aria-label={`Remove ${c.name}`}
                        disabled={busy}
                        onClick={() =>
                          save(
                            `facilities/${facility.id}/catalog/${c.id}`,
                            { ...c, version: facility.version, id: undefined },
                            "DELETE",
                          ).catch(() => {})
                        }
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="catalog-empty">
          <FlaskConical size={30} />
          <h3>Your services start here.</h3>
          <p>Add the tests and consultations your hospital offers.</p>
        </div>
      )}
      <small className="catalog-note">
        Catalog prices are hospital declarations. Referral matching currently
        supports reviewed primary-care OPD; additional tests remain catalog
        information.
      </small>
    </section>
  );
}
