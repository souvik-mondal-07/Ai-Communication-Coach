import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TrendsData } from "@/types/analytics";
import { Empty } from "./AnalyticsStates";
import { buildChartRows, DIRECTION_LABEL, formatPeriod, hasChartData } from "./analyticsUtils";

const GROUPS = {
  performance: { label: "Performance", keys: ["technical", "communication", "confidence", "overall"], max: 100 },
  speaking: { label: "Speaking", keys: ["filler_rate", "speaking_speed"], max: undefined },
  structure: { label: "Structure & clarity", keys: ["structure", "clarity"], max: 100 },
} as const;
type GroupKey = keyof typeof GROUPS;
const COLORS = ["#35d0ba", "#7d8cf0", "#f5a623", "#e5484d"];

export function TrendsSection({ data }: { data: TrendsData }) {
  const [group, setGroup] = useState<GroupKey>("performance");
  const g = GROUPS[group];
  const keys = [...g.keys];
  const rows = buildChartRows(data.series, keys);

  return (
    <div>
      <div role="tablist" aria-label="Trend metric group" className="mb-3 flex flex-wrap gap-2">
        {(Object.keys(GROUPS) as GroupKey[]).map((k) => (
          <button
            key={k}
            role="tab"
            aria-selected={group === k}
            onClick={() => setGroup(k)}
            className={`rounded-full border px-3 py-1 text-xs ${
              group === k ? "border-signal text-signal" : "border-border text-text-secondary hover:border-border-strong"
            }`}
          >
            {GROUPS[k].label}
          </button>
        ))}
      </div>
      {!hasChartData(data.series, keys) ? (
        <Empty>No data for these metrics in this range yet.</Empty>
      ) : rows.length < 2 ? (
        <Empty>Only one time period has data so far. Trends appear after more practice.</Empty>
      ) : (
        <div className="h-64" role="img" aria-label={`${g.label} trend chart by ${data.granularity}`}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}>
              <CartesianGrid stroke="#232c3a" vertical={false} />
              <XAxis dataKey="period" tickFormatter={formatPeriod} stroke="#6c7889" fontSize={11} tickLine={false} />
              <YAxis stroke="#6c7889" fontSize={11} tickLine={false} domain={g.max ? [0, g.max] : ["auto", "auto"]} />
              <Tooltip
                labelFormatter={(l) => formatPeriod(String(l))}
                contentStyle={{ background: "#19212c", border: "1px solid #2f3b4d", borderRadius: 6, fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {keys.map((k, i) => (
                <Line
                  key={k}
                  type="monotone"
                  dataKey={k}
                  name={data.series[k]?.label ?? k}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  connectNulls={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
        {keys.map((k) => (
          <li key={k}>
            {data.series[k]?.label}: <span className="text-text-secondary">{DIRECTION_LABEL[data.series[k]?.direction ?? "insufficient_data"]}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
