"use client";
import { useEffect, useRef, useState } from "react";
import type { Map as LibreMap, Marker } from "maplibre-gl";
import type { Facility, State } from "@/lib/api";
export function PilotMap({
  state,
  selected,
  onSelect,
}: {
  state: State;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null),
    map = useRef<LibreMap | null>(null),
    markers = useRef<Marker[]>([]);
  const [ready, setReady] = useState(false),
    [streets, setStreets] = useState(false),
    [failed, setFailed] = useState(false),
    [tileError, setTileError] = useState(false);
  const choose = useRef(onSelect);
  choose.current = onSelect;
  useEffect(() => {
    let disposed = false;
    let observer: ResizeObserver | undefined;
    import("maplibre-gl")
      .then((lib) => {
        if (disposed || !container.current) return;
        try {
          lib.setWorkerUrl(
            new URL(
              "maplibre-gl/dist/maplibre-gl-worker.mjs",
              import.meta.url,
            ).toString(),
          );
          const m = new lib.Map({
            container: container.current,
            center: [73.055, 33.706],
            zoom: 11.8,
            attributionControl: false,
            style: {
              version: 8,
              sources: {},
              layers: [
                {
                  id: "land",
                  type: "background",
                  paint: { "background-color": "#eaf0ed" },
                },
              ],
            },
          });
          map.current = m;
          m.addControl(
            new lib.NavigationControl({ showCompass: false }),
            "top-right",
          );
          m.addControl(new lib.AttributionControl({ compact: false }));
          m.on("load", () => {
            if (disposed) return;
            const zones = state.config.zones.map((z) => ({
              type: "Feature" as const,
              properties: { name: z.name },
              geometry: {
                type: "Point" as const,
                coordinates: [z.longitude, z.latitude],
              },
            }));
            m.addSource("pilot-zones", {
              type: "geojson",
              data: { type: "FeatureCollection", features: zones },
            });
            m.addLayer({
              id: "pilot-zones",
              type: "circle",
              source: "pilot-zones",
              paint: {
                "circle-radius": 65,
                "circle-color": "#789da8",
                "circle-opacity": 0.12,
                "circle-stroke-width": 1,
                "circle-stroke-color": "#a9bfbd",
              },
            });
            setReady(true);
          });
          m.on("error", () => setTileError(true));
          observer = new ResizeObserver(() => m.resize());
          observer.observe(container.current);
        } catch {
          setFailed(true);
        }
      })
      .catch(() => setFailed(true));
    return () => {
      disposed = true;
      observer?.disconnect();
      map.current?.remove();
      map.current = null;
    };
    // Geography is a fixed, bundled pilot context.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (!ready || !map.current) return;
    let disposed = false;
    import("maplibre-gl").then((lib) => {
      if (disposed || !map.current) return;
      markers.current.forEach((m) => m.remove());
      markers.current = [];
      const bounds = new lib.LngLatBounds();
      state.facilities.forEach((f) => {
        const b = document.createElement("button");
        const status = f.capacities[0]?.status || "UNKNOWN";
        b.className = `map-pin ${status.toLowerCase()} ${selected === f.id ? "selected" : ""}`;
        b.textContent = f.id;
        b.title = `${f.name} · ${status.toLowerCase()}`;
        b.setAttribute("aria-label", `Select ${f.name}`);
        b.onclick = () => choose.current(f.id);
        markers.current.push(
          new lib.Marker({ element: b })
            .setLngLat([f.longitude, f.latitude])
            .addTo(map.current!),
        );
        bounds.extend([f.longitude, f.latitude]);
      });
      if (!selected && !bounds.isEmpty())
        map.current.fitBounds(bounds, {
          padding: 65,
          maxZoom: 12.5,
          duration: 0,
        });
      state.config.zones.forEach((z) => {
        const label = document.createElement("div");
        label.className = "zone-label";
        const count = state.summary?.zones.find((x) => x.zone === z.id)?.count;
        label.textContent = `${z.id}${count === undefined ? "" : ` · ${count} unresolved`}`;
        markers.current.push(
          new lib.Marker({ element: label, anchor: "bottom", offset: [0, -28] })
            .setLngLat([z.longitude, z.latitude])
            .addTo(map.current!),
        );
      });
    });
    return () => {
      disposed = true;
    };
  }, [state, selected, ready]);
  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    if (streets) {
      if (!m.getSource("streets")) {
        m.addSource("streets", {
          type: "raster",
          tiles: [
            process.env.NEXT_PUBLIC_MAP_TILE_URL ||
              "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
          ],
          tileSize: 256,
          attribution:
            '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
        });
        m.addLayer(
          { id: "streets", type: "raster", source: "streets" },
          "pilot-zones",
        );
      }
      m.setLayoutProperty("streets", "visibility", "visible");
    } else if (m.getLayer("streets"))
      m.setLayoutProperty("streets", "visibility", "none");
  }, [streets, ready]);
  return (
    <div className="pilot-map">
      <div ref={container} className="map-canvas" />
      {failed && (
        <svg
          className="map-canvas"
          viewBox="0 0 700 500"
          aria-label="Offline coordinate map"
        >
          {state.facilities.map((f) => (
            <g key={f.id} onClick={() => onSelect(f.id)}>
              <circle
                cx={(f.longitude - 72.94) * 2400}
                cy={480 - (f.latitude - 33.62) * 2700}
                r="15"
                fill="#536cc3"
              />
              <text
                x={(f.longitude - 72.94) * 2400}
                y={480 - (f.latitude - 33.62) * 2700 + 4}
                textAnchor="middle"
                fill="white"
                fontSize="10"
              >
                {f.id}
              </text>
            </g>
          ))}
        </svg>
      )}
      <div className="map-caption">
        <strong>Islamabad pilot network</strong>
        <span>
          {streets && !tileError
            ? "Street context · public directory coordinates"
            : "Bundled coordinate view · available offline"}
        </span>
        <span>
          Circles show demo catchments, not boundaries or travel access.
        </span>
      </div>
      <button className="map-toggle" onClick={() => setStreets(!streets)}>
        {streets ? "Use offline map" : "Show street context"}
      </button>
      {tileError && streets && (
        <div className="map-notice">
          Street tiles unavailable. Bundled pins and pilot zones remain visible.
        </div>
      )}
      <div className="map-legend">
        <span>
          <i className="green" />
          Available
        </span>
        <span>
          <i className="amber" />
          Limited
        </span>
        <span>
          <i className="red" />
          Exhausted
        </span>
        <span>
          <i className="grey" />
          Unknown / out of scope
        </span>
      </div>
    </div>
  );
}
