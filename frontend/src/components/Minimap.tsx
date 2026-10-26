import { useState } from "react";
import type { MapLayer } from "../lib/api";

export interface Marker {
  key: string;
  left: number; // 0..1, from the backend's fitted world->minimap transform
  top: number;
  color: string;
  label: string;
  size?: number;
  shape?: "dot" | "x" | "ring";
  emphasis?: boolean;
  onClick?: () => void;
}

const SURFACE = "#171a21";

export default function Minimap({
  map,
  markers,
  maxWidth = 560,
  caption,
}: {
  map: MapLayer;
  markers: Marker[];
  maxWidth?: number;
  caption?: string;
}) {
  const [hover, setHover] = useState<Marker | null>(null);
  const S = 1000;
  return (
    <figure className="w-full" style={{ maxWidth }}>
      <div className="relative">
        <svg viewBox={`0 0 ${S} ${S}`} className="w-full rounded-xl bg-panel2 border border-line" role="img" aria-label={caption || "Minimap"}>
          {map.image && (
            <image href={map.image} x={0} y={0} width={S} height={S} style={{ filter: "brightness(2.2) contrast(1.1)" }} />
          )}
          {map.lanes.map((lane) => {
            const mid = lane.pts[Math.floor(lane.pts.length / 2)];
            return (
              <g key={lane.id} aria-hidden>
                <polyline
                  points={lane.pts.map(([l, t]) => `${l * S},${t * S}`).join(" ")}
                  fill="none"
                  stroke={lane.color}
                  strokeWidth={7}
                  strokeOpacity={0.45}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
                <text
                  x={mid[0] * S}
                  y={mid[1] * S - 14}
                  textAnchor="middle"
                  fill="#f4f5f7"
                  fontSize={30}
                  fontWeight={700}
                  stroke="#0e1014"
                  strokeWidth={6}
                  paintOrder="stroke"
                >
                  {lane.name}
                </text>
              </g>
            );
          })}
          {markers.map((m) => {
            const cx = m.left * S;
            const cy = m.top * S;
            const r = (m.size ?? 9) * (m.emphasis ? 1.4 : 1);
            return (
              <g
                key={m.key}
                onMouseEnter={() => setHover(m)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(m)}
                onBlur={() => setHover(null)}
                onClick={m.onClick}
                onKeyDown={(e) => {
                  if (m.onClick && (e.key === "Enter" || e.key === " ")) m.onClick();
                }}
                tabIndex={m.onClick ? 0 : -1}
                role={m.onClick ? "button" : undefined}
                aria-label={m.label}
                style={{ cursor: m.onClick ? "pointer" : "default" }}
              >
                {/* Hit target larger than the mark */}
                <circle cx={cx} cy={cy} r={r + 12} fill="transparent" />
                {m.shape === "x" ? (
                  <g stroke={m.color} strokeWidth={6} strokeLinecap="round">
                    <line x1={cx - r} y1={cy - r} x2={cx + r} y2={cy + r} stroke={SURFACE} strokeWidth={10} />
                    <line x1={cx - r} y1={cy + r} x2={cx + r} y2={cy - r} stroke={SURFACE} strokeWidth={10} />
                    <line x1={cx - r} y1={cy - r} x2={cx + r} y2={cy + r} />
                    <line x1={cx - r} y1={cy + r} x2={cx + r} y2={cy - r} />
                  </g>
                ) : m.shape === "ring" ? (
                  <circle cx={cx} cy={cy} r={r} fill="none" stroke={m.color} strokeWidth={5} />
                ) : (
                  <circle cx={cx} cy={cy} r={r} fill={m.color} stroke={m.emphasis ? "#ffffff" : SURFACE} strokeWidth={m.emphasis ? 5 : 3} />
                )}
              </g>
            );
          })}
        </svg>
        {hover && (
          <div
            className="pointer-events-none absolute z-10 rounded-lg bg-bg border border-line px-3 py-1 text-sm shadow-lg"
            style={{
              left: `${Math.min(80, hover.left * 100)}%`,
              top: `${Math.max(0, hover.top * 100 - 9)}%`,
            }}
          >
            {hover.label}
          </div>
        )}
      </div>
      {caption && <figcaption className="mt-2 text-sm text-muted">{caption}</figcaption>}
    </figure>
  );
}
