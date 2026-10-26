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

const YOU = "#3987e5";
const AVG = "#c3c2b7";

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
            <span className="inline-block w-6 border-t-2 border-dashed" style={{ borderColor: AVG }} /> Rank average
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
            <CartesianGrid stroke="#2c2c2a" vertical={false} />
            <XAxis
              dataKey="t"
              type="number"
              domain={[0, "dataMax"]}
              tickFormatter={(t) => clock(t)}
              stroke="#898781"
              tick={{ fill: "#9a9890", fontSize: 14 }}
            />
            <YAxis tickFormatter={compact} stroke="#898781" tick={{ fill: "#9a9890", fontSize: 14 }} width={48} />
            <Tooltip
              contentStyle={{ background: "#0e1014", border: "1px solid #2e3440", borderRadius: 12 }}
              labelFormatter={(t) => `At ${clock(Number(t))}`}
              formatter={(v: number, name: string) => [num(v), name === "you" ? "You" : "Rank average"]}
            />
            {time != null && <ReferenceLine x={time} stroke="#f4f5f7" strokeWidth={2} />}
            {hasAvg && (
              <Line
                dataKey="avg"
                stroke={AVG}
                strokeWidth={2}
                strokeDasharray="6 5"
                dot={false}
                connectNulls
                isAnimationActive={false}
                label={(p: { index: number; x: number; y: number }) =>
                  p.index === lastAvg ? (
                    <text key="avg-label" x={p.x + 8} y={p.y + 5} fill="#c3c2b7" fontSize={14}>
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
              dot={{ r: 4, fill: YOU, stroke: "#171a21", strokeWidth: 2 }}
              activeDot={{ r: 6 }}
              isAnimationActive={false}
              label={(p: { index: number; x: number; y: number }) =>
                p.index === series.length - 1 ? (
                  <text key="you-label" x={p.x + 8} y={p.y + 5} fill="#f4f5f7" fontSize={14} fontWeight={700}>
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
