"use client";
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
  const position = (f: Facility) => ({
    x: 65 + ((f.longitude - 66.99) / 0.12) * 650,
    y: 390 - ((f.latitude - 24.84) / 0.13) * 330,
  });
  return (
    <div className="map-canvas">
      <svg
        viewBox="0 0 800 460"
        role="img"
        aria-label="Schematic of demo facilities across Karachi zones"
      >
        <defs>
          <pattern
            id="grid"
            width="44"
            height="44"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(-25)"
          >
            <rect width="44" height="44" fill="#f0f2f5" />
            <rect x="5" y="5" width="31" height="28" rx="3" fill="#e5e9ee" />
            <path d="M0 0H44M0 0V44" stroke="white" strokeWidth="7" />
          </pattern>
        </defs>
        <rect width="800" height="460" fill="url(#grid)" />
        <path
          d="M-30 310 Q210 235 400 270 T830 195"
          stroke="#fff"
          strokeWidth="30"
          fill="none"
        />
        <path
          d="M180 -30 Q245 200 535 490"
          stroke="#fff"
          strokeWidth="22"
          fill="none"
        />
        <path
          d="M-40 435 Q160 385 200 460"
          stroke="#cbdde6"
          strokeWidth="80"
          fill="none"
        />
        <g
          fill="#8c97a6"
          fontSize="12"
          fontFamily="sans-serif"
          letterSpacing="3"
        >
          <text x="330" y="110">
            NORTH
          </text>
          <text x="650" y="280">
            EAST
          </text>
          <text x="50" y="170">
            WEST
          </text>
          <text x="355" y="230">
            CENTRAL
          </text>
          <text x="350" y="420">
            SOUTH
          </text>
        </g>
        {facilities.map((f) => {
          const { x, y } = position(f);
          const free = f.capacities.reduce((n, c) => n + c.available, 0);
          const active = selected === f.id;
          return (
            <g key={f.id} transform={`translate(${x},${y})`}>
              {active && <circle r="39" fill="#5264e3" opacity=".1" />}
              <circle
                r="28"
                fill={free ? "#6475e9" : "#e68c8b"}
                opacity=".13"
              />
              <path
                d="M-20 2 L0 -9 L20 2 L0 14Z"
                fill={free ? "#8996f0" : "#ecaaaa"}
              />
              <path
                d="M-20 2 V15 L0 27 V14Z"
                fill={free ? "#5264df" : "#d87475"}
              />
              <path
                d="M0 14 L20 2 V15 L0 27Z"
                fill={free ? "#6b7bea" : "#e88b89"}
              />
              <circle
                cy="-14"
                r="15"
                fill={active ? "#202c55" : "#fff"}
                stroke={active ? "#202c55" : "#d9dfea"}
              />
              <text
                y="-10"
                textAnchor="middle"
                fontSize="11"
                fill={active ? "white" : "#34415c"}
                fontWeight="700"
              >
                {free}
              </text>
            </g>
          );
        })}
      </svg>
      {facilities.map((f) => {
        const { x, y } = position(f);
        return (
          <button
            key={f.id}
            className="map-hit"
            style={{ left: `${x / 8}%`, top: `${y / 4.6}%` }}
            onClick={() => onSelect(f.id)}
            aria-label={`Select ${f.name}`}
            title={f.name}
          />
        );
      })}
      <div className="map-legend">
        <span>
          <i className="dot indigo" />
          Capacity available
        </span>
        <span>
          <i className="dot coral" />
          At capacity
        </span>
      </div>
      <div className="map-note">Karachi · schematic view</div>
    </div>
  );
}
