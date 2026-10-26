import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { clock, compact, num } from "../lib/format";
import { useThemeColors } from "../lib/theme";

const YOU = "#3987e5";

interface Point {
  t: number;
  you: number;
  avg: number | null;
}

export default function SoulsChart({
  series,
  time,
  onPick,
}: {
  series: Point[];
  time: number | null;
  onPick: (t: number) => void;
}) {
  const c = useThemeColors();
  const hasAvg = series.some((p) => p.avg != null);
  let lastAvg = -1;
  series.forEach((p, i) => {
    if (p.avg != null) lastAvg = i;
  });
  return (
    <div>
      <div className="flex flex-wrap gap-4 text-sm text-dim mb-2" aria-hidden>
        <span className="inline-flex items-center gap-2">
          <span className="inline-block h-0.5 w-6" style={{ background: YOU }} /> You
        </span>
        {hasAvg && (
          <span className="inline-flex items-center gap-2">
            <span className="inline-block w-6 border-t-2 border-dashed" style={{ borderColor: c.dim }} /> Rank average
          </span>
        )}
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer>
          <LineChart
            data={series}
            margin={{ top: 10, right: 70, bottom: 0, left: 0 }}
            onClick={(e) => {
              if (e && e.activeLabel != null) onPick(Number(e.activeLabel));
            }}
          >
            <CartesianGrid stroke={c.line} vertical={false} />
            <XAxis
              dataKey="t"
              type="number"
              domain={[0, "dataMax"]}
              tickFormatter={(t) => clock(t)}
              stroke={c.muted}
              tick={{ fill: c.muted, fontSize: 14 }}
            />
            <YAxis tickFormatter={compact} stroke={c.muted} tick={{ fill: c.muted, fontSize: 14 }} width={48} />
            <Tooltip
              contentStyle={{ background: c.bg, border: `1px solid ${c.line}`, borderRadius: 12, color: c.ink }}
              labelFormatter={(t) => `At ${clock(Number(t))}`}
              formatter={(v: number, name: string) => [num(v), name === "you" ? "You" : "Rank average"]}
            />
            {time != null && <ReferenceLine x={time} stroke={c.ink} strokeWidth={2} />}
            {hasAvg && (
              <Line
                dataKey="avg"
                stroke={c.dim}
                strokeWidth={2}
                strokeDasharray="6 5"
                dot={false}
                connectNulls
                isAnimationActive={false}
                label={(p: { index: number; x: number; y: number }) =>
                  p.index === lastAvg ? (
                    <text key="avg-label" x={p.x + 8} y={p.y + 5} fill={c.dim} fontSize={14}>
                      Rank avg
                    </text>
                  ) : (
                    <g key={`a${p.index}`} />
                  )
                }
              />
            )}
            <Line
              dataKey="you"
              stroke={YOU}
              strokeWidth={2.5}
              dot={{ r: 4, fill: YOU, stroke: c.panel, strokeWidth: 2 }}
              activeDot={{ r: 6 }}
              isAnimationActive={false}
              label={(p: { index: number; x: number; y: number }) =>
                p.index === series.length - 1 ? (
                  <text key="you-label" x={p.x + 8} y={p.y + 5} fill={c.ink} fontSize={14} fontWeight={700}>
                    You
                  </text>
                ) : (
                  <g key={`y${p.index}`} />
                )
              }
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
