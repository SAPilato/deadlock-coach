import { ReactNode, useRef } from "react";

export const S = 1000; // viewBox size; relative positions are multiplied by this
export const SURFACE = "#171a21";
// Game data pairs Hidden King with amber and Archmother with sapphire (generic-data map_districts, color_team1/2).
export const TEAM_COLORS = ["#d95926", "#3987e5"]; // team 0 (Hidden King), team 1 (Archmother)
// "Your side" colours, independent of which team you were on. Same as the match report.
export const ALLY = "#3987e5";
export const ENEMY = "#d95926";

export interface Hover {
  left: number;
  top: number;
  title: string;
  lines: string[];
}

export default function MapCanvas({
  image,
  overlays = [],
  children,
  hover,
  onClick,
  caption,
  crosshair = false,
}: {
  image?: string;
  overlays?: string[];
  children: ReactNode;
  hover?: Hover | null;
  onClick?: (left: number, top: number) => void;
  caption?: ReactNode;
  crosshair?: boolean;
}) {
  const ref = useRef<SVGSVGElement>(null);
  return (
    <figure className="w-full max-w-[680px]">
      <div className="relative">
        <svg
          ref={ref}
          viewBox={`0 0 ${S} ${S}`}
          className={`w-full rounded-xl border border-line bg-panel2 ${crosshair ? "cursor-crosshair" : ""}`}
          role="img"
          aria-label="Deadlock minimap"
          onClick={(e) => {
            if (!onClick || !ref.current) return;
            const r = ref.current.getBoundingClientRect();
            onClick((e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
          }}
        >
          {image && <image href={image} width={S} height={S} style={{ filter: "brightness(2.2) contrast(1.1)" }} />}
          {overlays.map((src) => (
            <image key={src} href={src} width={S} height={S} opacity={0.8} />
          ))}
          {children}
        </svg>
        {hover && (
          <div
            className="pointer-events-none absolute z-10 max-w-[18rem] rounded-xl border border-line bg-bg px-3 py-2 text-sm shadow-xl"
            style={{
              left: `${Math.min(62, hover.left * 100 + 2)}%`,
              top: `${Math.min(85, hover.top * 100 + 2)}%`,
            }}
          >
            <div className="font-bold text-base">{hover.title}</div>
            {hover.lines.map((l) => (
              <div key={l} className="text-dim">
                {l}
              </div>
            ))}
          </div>
        )}
      </div>
      {caption && <figcaption className="mt-2 text-sm text-muted">{caption}</figcaption>}
    </figure>
  );
}

export function Lanes({ lanes, width = 7 }: { lanes: { id: number; name: string; color: string; pts: [number, number][] }[]; width?: number }) {
  return (
    <g aria-hidden>
      {lanes.map((l) => (
        <polyline
          key={l.id}
          points={l.pts.map(([a, b]) => `${a * S},${b * S}`).join(" ")}
          fill="none"
          stroke={l.color}
          strokeWidth={width}
          strokeOpacity={0.45}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      ))}
    </g>
  );
}

export function Glyph({
  left,
  top,
  ch,
  color,
  size = 22,
  label,
  onHover,
  onLeave,
}: {
  left: number;
  top: number;
  ch: string;
  color: string;
  size?: number;
  label?: string;
  onHover?: () => void;
  onLeave?: () => void;
}) {
  return (
    <g onMouseEnter={onHover} onMouseLeave={onLeave} onFocus={onHover} onBlur={onLeave} tabIndex={onHover ? 0 : -1} aria-label={label}>
      <circle cx={left * S} cy={top * S} r={size * 0.8} fill="transparent" />
      <text
        x={left * S}
        y={top * S}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={size}
        fontWeight={700}
        fill={color}
        stroke={SURFACE}
        strokeWidth={5}
        paintOrder="stroke"
      >
        {ch}
      </text>
    </g>
  );
}
