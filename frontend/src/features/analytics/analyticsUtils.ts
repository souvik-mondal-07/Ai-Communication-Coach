import type { AnalyticsRange, ChangeLabel, Direction, TrendSeries } from "@/types/analytics";

/** Pure helpers for the analytics UI (kept DOM-free so they are unit-testable). */

export const RANGE_OPTIONS: { value: AnalyticsRange; label: string }[] = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "all", label: "All time" },
];

/** `null`/`undefined` is "no data" and is always shown as N/A -- never as 0. */
export function formatScore(value: number | null | undefined, suffix = ""): string {
  return value === null || value === undefined ? "N/A" : `${value}${suffix}`;
}

export function formatChange(change: number | null | undefined): string {
  if (change === null || change === undefined) return "N/A";
  return change > 0 ? `+${change}` : `${change}`;
}

export const CHANGE_TONE: Record<Exclude<ChangeLabel, null>, "good" | "neutral" | "warn" | "bad"> = {
  "Significant improvement": "good",
  Improving: "good",
  Stable: "neutral",
  "Slight decline": "warn",
  "Needs attention": "bad",
};

export const TONE_CLASS = {
  good: "text-signal",
  neutral: "text-text-secondary",
  warn: "text-warn",
  bad: "text-danger",
} as const;

export function changeToneClass(label: ChangeLabel): string {
  return label ? TONE_CLASS[CHANGE_TONE[label]] : "text-text-muted";
}

export const DIRECTION_LABEL: Record<Direction, string> = {
  improving: "Improving",
  stable: "Stable",
  declining: "Declining",
  insufficient_data: "Not enough data",
};

export function bandColor(score: number | null): string {
  if (score === null) return "#6c7889";
  if (score >= 75) return "#35d0ba";
  if (score < 60) return "#e5484d";
  return "#f5a623";
}

export interface ChartRow {
  period: string;
  [seriesKey: string]: number | string | null;
}

/**
 * Merge several backend series into one row-per-period dataset for a multi-line chart.
 * Periods where a series has no data stay `null` (a gap), never 0.
 */
export function buildChartRows(series: Record<string, TrendSeries>, keys: string[]): ChartRow[] {
  const periods = new Set<string>();
  for (const key of keys) for (const p of series[key]?.points ?? []) periods.add(p.period);
  return [...periods].sort().map((period) => {
    const row: ChartRow = { period };
    for (const key of keys) {
      const point = series[key]?.points.find((p) => p.period === period);
      row[key] = point?.value ?? null;
    }
    return row;
  });
}

export function hasChartData(series: Record<string, TrendSeries>, keys: string[]): boolean {
  return keys.some((k) => (series[k]?.points.length ?? 0) > 0);
}

/** "2026-10-05" -> "Oct 5"; "2026-10" -> "Oct 2026". Falls back to the raw label. */
export function formatPeriod(period: string): string {
  const day = /^(\d{4})-(\d{2})-(\d{2})$/.exec(period);
  const month = /^(\d{4})-(\d{2})$/.exec(period);
  const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  if (day) return `${names[Number(day[2]) - 1]} ${Number(day[3])}`;
  if (month) return `${names[Number(month[2]) - 1]} ${month[1]}`;
  return period;
}

export const WEAKNESS_SEVERITY_CLASS = { high: "text-danger", medium: "text-warn", low: "text-text-secondary" } as const;

export type LoadState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };
