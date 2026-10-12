import type { OverviewSessionCounts, ProgressOverview, TrendsResponse } from "@/types/progress";

export function greetingFor(hour: number): string {
  if (hour < 5) return "Working late";
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

/** First word of the display name, or a neutral fallback when it is missing. */
export function firstName(name: string | undefined | null): string {
  return name?.trim().split(/\s+/)[0] || "there";
}

/** "78/100", or null when there is no score. Scores come from the backend; never computed here. */
export function formatScore(score: number | null | undefined): string | null {
  return typeof score === "number" && Number.isFinite(score) ? `${Math.round(score)}/100` : null;
}

export function totalCompleted(counts: OverviewSessionCounts): number {
  return Object.values(counts).reduce((sum, c) => sum + c.completed, 0);
}

export function totalStarted(counts: OverviewSessionCounts): number {
  return Object.values(counts).reduce((sum, c) => sum + c.total, 0);
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

/** Whole-number percentage; 0 when there is nothing to divide by. */
export function percent(done: number, total: number): number {
  if (!Number.isFinite(done) || !Number.isFinite(total) || total <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((done / total) * 100)));
}

/** "2 hours ago", "1 day ago", "Just now". Returns "" for an unparseable date. */
export function relativeTime(iso: string, now: number = Date.now()): string {
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return "";
  const mins = Math.floor(Math.max(0, now - t) / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} day${days === 1 ? "" : "s"} ago`;
  return new Date(t).toLocaleDateString();
}

export interface SkillAxis {
  key: string;
  label: string;
  /** 0-100 from the backend, or null when the user has no data for this dimension. */
  value: number | null;
}

/**
 * Radar axes built only from values the backend already reports. There is no
 * "problem solving" measure in the progress model, so pressure-training score
 * takes the fifth axis rather than inventing a number.
 */
export function buildSkillAxes(o: ProgressOverview): SkillAxis[] {
  const num = (n: number | null | undefined) => (typeof n === "number" && Number.isFinite(n) ? Math.max(0, Math.min(100, Math.round(n))) : null);
  return [
    { key: "security", label: "Security", value: num(o.cybersecurity_performance.average_score) },
    { key: "communication", label: "Communication", value: num(o.communication_performance?.overall_score) },
    { key: "interview", label: "Interview", value: num(o.interview_performance?.overall_score) },
    { key: "confidence", label: "Confidence", value: num(o.communication_performance?.confidence_score) },
    { key: "pressure", label: "Under Pressure", value: num(o.pressure_performance?.overall_score) },
  ];
}

export interface MergedTrendRow {
  period: string;
  technical: number | null;
  communication: number | null;
  interview: number | null;
  overall: number | null;
}

/** One row per period across all series; a series with no point that day is null (the line skips it). */
export function mergeTrends(dims: TrendsResponse["dimensions"]): MergedTrendRow[] {
  const keys = ["technical", "communication", "interview", "overall"] as const;
  const rows = new Map<string, MergedTrendRow>();
  for (const k of keys) {
    for (const p of dims[k]?.points ?? []) {
      const row = rows.get(p.period) ?? { period: p.period, technical: null, communication: null, interview: null, overall: null };
      row[k] = p.average_score;
      rows.set(p.period, row);
    }
  }
  return [...rows.values()].sort((a, b) => a.period.localeCompare(b.period));
}
