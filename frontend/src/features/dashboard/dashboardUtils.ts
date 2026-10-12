import type { OverviewSessionCounts } from "@/types/progress";

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
