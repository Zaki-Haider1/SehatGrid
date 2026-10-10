import { Facility } from "@/lib/api";

export function HospitalProfile({ facility }: { facility: Facility }) {
  const profile = facility.profile;
  const point = `${facility.latitude.toFixed(6)}, ${facility.longitude.toFixed(6)}`;
  const mapUrl = `https://www.openstreetmap.org/?mlat=${facility.latitude}&mlon=${facility.longitude}#map=17/${facility.latitude}/${facility.longitude}`;
  return (
    <div className="hospital-profile">
      <div className="hospital-badges">
        <span
          className={profile.ownership === "Private" ? "private-badge" : ""}
        >
          {profile.ownership || "Unverified provider"}
        </span>
        {profile.sector && <span>{profile.sector}</span>}
      </div>
      <p className="hospital-address">
        {profile.address || "Address has not been verified."}
      </p>
      <div className="hospital-links">
        {profile.phone && (
          <a href={`tel:${profile.phone.replace(/[^+\d]/g, "")}`}>
            {profile.phone}
          </a>
        )}
        {profile.website && (
          <a href={profile.website} target="_blank" rel="noreferrer">
            Hospital website ↗
          </a>
        )}
        <a href={mapUrl} target="_blank" rel="noreferrer">
          Open location ↗
        </a>
      </div>
      <details className="hospital-evidence">
        <summary>Hospital information &amp; sources</summary>
        {!!profile.departments?.length && (
          <p>
            <strong>Published services:</strong>{" "}
            {profile.departments.join(", ")}. These do not confirm availability.
          </p>
        )}
        {profile.emergency && (
          <p>
            <strong>Emergency:</strong> {profile.emergency}
          </p>
        )}
        {profile.hours && (
          <p>
            <strong>Published hours:</strong> {profile.hours}
          </p>
        )}
        {profile.email && (
          <p>
            <strong>Email:</strong>{" "}
            <a href={`mailto:${profile.email}`}>{profile.email}</a>
          </p>
        )}
        <p>
          <strong>Coordinates:</strong> {point}
        </p>
        <p>
          {profile.coordinate_method ||
            "Coordinates submitted by the registering provider."}
          . {profile.coordinate_note || "Location has not been verified."}
        </p>
        {profile.coordinate_source && (
          <a href={profile.coordinate_source} target="_blank" rel="noreferrer">
            Coordinate source ↗
          </a>
        )}
        {profile.notes && <p>{profile.notes}</p>}
        <ul>
          {profile.directory_sources?.map((source) => (
            <li key={source.url}>
              <a href={source.url} target="_blank" rel="noreferrer">
                {source.title} ↗
              </a>
            </li>
          ))}
        </ul>
        {profile.checked_on && (
          <p>
            Sources checked {profile.checked_on}. Contact the hospital to
            confirm current details.
          </p>
        )}
      </details>
    </div>
  );
}
