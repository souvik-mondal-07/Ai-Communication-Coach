import { useEffect, useMemo, useState } from "react";
import { ChartColumn, ChevronDown, TrendingUp } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { buttonVariants } from "@/components/ui/button-variants";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPeriod } from "@/features/analytics/analyticsUtils";
import { mergeTrends, type MergedTrendRow } from "@/features/dashboard/dashboardUtils";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import { reveal } from "@/lib/motion";
import * as progressService from "@/services/progressService";
import type { TrendPeriod, TrendsResponse } from "@/types/progress";
import { getApiErrorMessage } from "@/utils/apiError";
import { chartLabelStyle, chartTooltipStyle } from "@/utils/chartTheme";
import { Link } from "react-router-dom";

const PERIODS: { value: TrendPeriod; label: string }[] = [
  { value: "7d", label: "Last 7 Days" },
  { value: "30d", label: "Last 30 Days" },
  { value: "90d", label: "Last 90 Days" },
];

const SERIES: { key: Exclude<keyof MergedTrendRow, "period">; label: string; color: string }[] = [
  { key: "technical", label: "Cybersecurity", color: "var(--color-signal)" },
  { key: "communication", label: "Communication", color: "var(--color-violet)" },
  { key: "interview", label: "Interview", color: "var(--color-cyan)" },
  { key: "overall", label: "Overall", color: "var(--color-success)" },
];

type Result = { key: string; data: TrendsResponse | null; message: string | null };

/** Multi-series score trend from /progress/trends. Nothing is generated client-side. */
export function LearningProgressCard() {
  const [period, setPeriod] = useState<TrendPeriod>("7d");
  const [nonce, setNonce] = useState(0);
  const [result, setResult] = useState<Result | null>(null);
  const [lastData, setLastData] = useState<TrendsResponse | null>(null);
  const reduce = usePrefersReducedMotion();
  const key = `${period}:${nonce}`;

  useEffect(() => {
    let active = true;
    progressService
      .getTrends(period)
      .then((data) => {
        if (!active) return;
        setResult({ key, data, message: null });
        setLastData(data);
      })
      .catch((err) => active && setResult({ key, data: null, message: getApiErrorMessage(err, "Couldn't load your learning progress.") }));
    return () => {
      active = false;
    };
  }, [period, nonce, key]);

  // Loading is derived: the latest result belongs to a different range/retry. The previous chart stays visible meanwhile.
  const isLoading = result?.key !== key;
  const error = !isLoading ? result?.message ?? null : null;
  const data = !isLoading && result?.data ? result.data : lastData;
  const state = { status: error ? "error" : isLoading ? "loading" : "ready", message: error ?? "", data: error ? null : data } as const;

  const rows = useMemo(() => (state.data ? mergeTrends(state.data.dimensions) : []), [state.data]);
  const enough = rows.length >= 2;
  const summary = useMemo(() => {
    const last = rows[rows.length - 1];
    if (!last) return "";
    return SERIES.map((s) => `${s.label} ${last[s.key] == null ? "no data" : Math.round(last[s.key] as number)}`).join(", ");
  }, [rows]);
  const r = reveal(5);

  return (
    <section aria-labelledby="progress-chart-title" className={`${r.className} flex flex-col rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-card`} style={r.style}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#2b2f8f]/70 text-[#9aa8ff]">
            <ChartColumn size={18} aria-hidden="true" />
          </span>
          <h2 id="progress-chart-title" className="font-display text-[15px] font-semibold text-text-primary">Your Learning Progress</h2>
        </div>
        <div className="relative">
          <select
            aria-label="Time range"
            value={period}
            onChange={(e) => setPeriod(e.target.value as TrendPeriod)}
            className="h-9 appearance-none rounded-[var(--radius-panel)] border border-border-strong bg-surface-raised pl-3 pr-8 text-sm text-text-primary transition-colors hover:border-border-input focus:outline-none focus-visible:ring-2 focus-visible:ring-signal/40"
          >
            {PERIODS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          <ChevronDown size={15} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted" aria-hidden="true" />
        </div>
      </div>

      <div className="mt-4 flex flex-1 flex-col">
        {state.status === "loading" && !state.data && (
          <div role="status" aria-label="Loading learning progress">
            <Skeleton className="h-64 w-full rounded-[var(--radius-panel)]" />
          </div>
        )}
        {state.status === "error" && <ErrorState message={state.message} onRetry={() => setNonce((n) => n + 1)} />}
        {state.data && !enough && (
          <EmptyState
            icon={TrendingUp}
            title="Not enough data for a trend yet"
            description="Complete sessions on a few different days and your scores over time will appear here."
            action={<Link to="/cybersecurity" className={buttonVariants({ variant: "secondary", size: "sm" })}>Start practicing</Link>}
          />
        )}
        {state.data && enough && (
          <div className={`flex flex-1 flex-col ${state.status === "loading" ? "opacity-60 transition-opacity" : "transition-opacity"}`}>
            <div className="min-h-56 flex-1" role="img" aria-label={`Score trend, ${PERIODS.find((p) => p.value === period)?.label}. Latest: ${summary}.`}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rows} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                  <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 4" vertical={false} />
                  <XAxis dataKey="period" tickFormatter={formatPeriod} stroke="var(--color-text-muted)" tickLine={false} axisLine={false} fontSize={12} tickMargin={8} minTickGap={16} />
                  <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} stroke="var(--color-text-muted)" tickLine={false} axisLine={false} fontSize={12} width={44} />
                  <Tooltip labelFormatter={(l) => formatPeriod(String(l))} contentStyle={chartTooltipStyle} labelStyle={chartLabelStyle} cursor={{ stroke: "var(--color-border-strong)" }} />
                  {SERIES.map((s) => (
                    <Line
                      key={s.key}
                      type="monotone"
                      dataKey={s.key}
                      name={s.label}
                      stroke={s.color}
                      strokeWidth={2}
                      dot={{ r: 3, strokeWidth: 0, fill: s.color }}
                      activeDot={{ r: 5 }}
                      connectNulls
                      isAnimationActive={!reduce}
                      animationDuration={900}
                      animationEasing="ease-out"
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <ul className="mt-2 flex flex-wrap items-center justify-center gap-x-6 gap-y-1.5 text-xs text-text-secondary" aria-label="Legend">
              {SERIES.map((s) => (
                <li key={s.key} className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} aria-hidden="true" />
                  {s.label}
                </li>
              ))}
            </ul>
            <div className="sr-only">
            <table>
              <caption>Average scores by day</caption>
              <thead>
                <tr><th>Day</th>{SERIES.map((s) => <th key={s.key}>{s.label}</th>)}</tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.period}>
                    <td>{formatPeriod(row.period)}</td>
                    {SERIES.map((s) => <td key={s.key}>{row[s.key] == null ? "no data" : Math.round(row[s.key] as number)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
