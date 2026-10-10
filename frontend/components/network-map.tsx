"use client";

import { useEffect, useRef, useState } from "react";
import type { Map as MapLibreMap, Marker } from "maplibre-gl";
import { Facility } from "@/lib/api";

export function NetworkMap({
  facilities,
  selected,
  onSelect,
}: {
  facilities: Facility[];
  selected: number | null;
  onSelect: (id: number) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const markers = useRef<Map<number, Marker>>(new Map());
  const select = useRef(onSelect);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const fitted = useRef(false);
  select.current = onSelect;

  useEffect(() => {
    let disposed = false;
    let observer: ResizeObserver | undefined;
    import("maplibre-gl")
      .then((lib) => {
        if (disposed || !container.current) return;
        try {
          // Explicit worker URL lets Next bundle the module and its shared imports.
          lib.setWorkerUrl(
            new URL(
              "maplibre-gl/dist/maplibre-gl-worker.mjs",
              import.meta.url,
            ).toString(),
          );
          const instance = new lib.Map({
            container: container.current,
            center: [73.055, 33.695],
            zoom: 12,
            maxZoom: 19,
            renderWorldCopies: false,
            cooperativeGestures: true,
            attributionControl: false,
            style: {
              version: 8,
              sources: {
                streets: {
                  type: "raster",
                  tiles: [
                    process.env.NEXT_PUBLIC_MAP_TILE_URL ||
                      "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                  ],
                  tileSize: 256,
                  maxzoom: 19,
                  attribution:
                    process.env.NEXT_PUBLIC_MAP_ATTRIBUTION ||
                    '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a>',
                },
              },
              layers: [{ id: "streets", type: "raster", source: "streets" }],
            },
          });
          map.current = instance;
          instance.addControl(
            new lib.NavigationControl({ showCompass: false }),
            "top-right",
          );
          instance.addControl(
            new lib.AttributionControl({ compact: false }),
            "bottom-right",
          );
          instance.on("load", () => {
            if (!disposed) setReady(true);
          });
          instance.on("error", () => {
            if (!disposed)
              setError(
                "Some map tiles could not load. Hospital details and coordinate links are still available.",
              );
          });
          observer = new ResizeObserver(() => instance.resize());
          observer.observe(container.current);
        } catch {
          setError(
            "The map requires WebGL. Use the hospital directory and coordinate links on this device.",
          );
        }
      })
      .catch(() => {
        if (!disposed)
          setError(
            "The map could not start. Use the hospital directory and coordinate links.",
          );
      });
    return () => {
      disposed = true;
      observer?.disconnect();
      markers.current.forEach((marker) => marker.remove());
      markers.current.clear();
      map.current?.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!ready || !map.current) return;
    let disposed = false;
    import("maplibre-gl").then((lib) => {
      if (disposed || !map.current) return;
      markers.current.forEach((marker) => marker.remove());
      markers.current.clear();
      const bounds = new lib.LngLatBounds();
      for (const facility of facilities) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `hospital-pin ${facility.profile.ownership === "Public" ? "public" : facility.profile.ownership === "Private" ? "private" : "unverified"}`;
        button.setAttribute("aria-label", `Select ${facility.name}`);
        button.setAttribute("aria-pressed", String(facility.id === selected));
        button.title = `${facility.name} · ${facility.profile.sector || facility.zone}`;
        button.textContent = "+";
        button.addEventListener("click", () => select.current(facility.id));
        // MapLibre accepts longitude first. No schematic projection or guessed offsets.
        const marker = new lib.Marker({ element: button, anchor: "center" })
          .setLngLat([facility.longitude, facility.latitude])
          .addTo(map.current);
        markers.current.set(facility.id, marker);
        bounds.extend([facility.longitude, facility.latitude]);
      }
      if (facilities.length && !fitted.current) {
        map.current.fitBounds(bounds, {
          padding: 55,
          maxZoom: 13,
          duration: 0,
        });
        fitted.current = true;
      }
    });
    return () => {
      disposed = true;
    };
  }, [facilities, ready, selected]);

  function fitHospitals() {
    if (!map.current || !facilities.length) return;
    const longitudes = facilities.map((f) => f.longitude);
    const latitudes = facilities.map((f) => f.latitude);
    map.current.fitBounds(
      [
        [Math.min(...longitudes), Math.min(...latitudes)],
        [Math.max(...longitudes), Math.max(...latitudes)],
      ],
      { padding: 55, maxZoom: 13, duration: 500 },
    );
  }

  return (
    <div className="geographic-map">
      <div className="map-canvas">
        <div
          ref={container}
          className="map-surface"
          role="region"
          aria-label="Geographic map of Islamabad hospitals"
        />
        {!ready && !error && (
          <div className="map-status" role="status">
            Loading Islamabad streets…
          </div>
        )}
        {error && (
          <div className="map-status map-error" role="status">
            {error}
          </div>
        )}
        <button className="map-fit" onClick={fitHospitals} disabled={!ready}>
          Fit hospitals
        </button>
        <div className="map-legend">
          <span>
            <i className="dot indigo" />
            Public
          </span>
          <span>
            <i className="dot teal" />
            Private
          </span>
        </div>
      </div>
      <p className="map-provenance">
        Campus locations from sourced coordinates · select a pin for details.{" "}
        <a
          href="https://www.openstreetmap.org/fixthemap"
          target="_blank"
          rel="noreferrer"
        >
          Report a map issue
        </a>
      </p>
    </div>
  );
}
