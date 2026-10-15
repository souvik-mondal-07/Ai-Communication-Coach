import type { FreshnessState, NewsCategoryId, NewsFreshness, SeverityLevel } from "@/types/news";

export type BadgeTone = "neutral" | "info" | "violet" | "success" | "warn" | "danger";

export const CATEGORY_TONE: Record<NewsCategoryId, BadgeTone> = {
  vulnerabilities: "warn",
  breaches: "danger",
  malware: "danger",
  "ai-security": "violet",
  appsec: "info",
  "cloud-network": "info",
  "bug-bounty": "success",
  "tools-research": "neutral",
  careers: "success",
  general: "neutral",
};

export const SEVERITY_TONE: Record<SeverityLevel, BadgeTone> = { critical: "danger", high: "warn", medium: "info", low: "neutral" };

export const SEVERITY_LABEL: Record<SeverityLevel, string> = { critical: "Critical", high: "High", medium: "Medium", low: "Low" };

/** Only http(s) URLs without embedded credentials may become a link. Anything else renders as no link. */
export function safeExternalUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value);
    if ((url.protocol !== "https:" && url.protocol !== "http:") || url.username || url.password) return null;
    return url.href;
  } catch {
    return null;
  }
}

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** "3 hours ago" for the last week, otherwise a short date. Returns null for a missing/invalid timestamp. */
export function formatPublished(iso: string | null | undefined, now: Date = new Date()): string | null {
  if (!iso) return null;
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return null;
  const diff = now.getTime() - then.getTime();
  if (diff < 0) return formatDate(then);
  if (diff < MINUTE) return "just now";
  if (diff < HOUR) return `${Math.floor(diff / MINUTE)} min ago`;
  if (diff < DAY) {
    const h = Math.floor(diff / HOUR);
    return `${h} hour${h === 1 ? "" : "s"} ago`;
  }
  if (diff < 7 * DAY) {
    const d = Math.floor(diff / DAY);
    return `${d} day${d === 1 ? "" : "s"} ago`;
  }
  return formatDate(then);
}

export function formatDate(date: Date): string {
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(date);
}

/** Honest freshness wording. Never says "live" or "real-time". */
export function describeFreshness(f: NewsFreshness, now: Date = new Date()): { tone: "ok" | "warn" | "info"; text: string } {
  const when = formatPublished(f.last_successful_refresh_at, now);
  const cadence = `Checked about every ${f.refresh_interval_minutes} minutes`;
  const stateText: Record<FreshnessState, string> = {
    fresh: when ? `Last updated ${when}. ${cadence}.` : cadence,
    stale: `Last updated ${when ?? "a while ago"}. Refreshing in the background; articles may be slightly out of date.`,
    degraded: `Showing cached articles. Last successful update ${when ?? "unknown"} — live refresh is currently failing.`,
    empty: f.refreshing ? "Fetching the latest articles…" : "No articles are available yet.",
  };
  const tone = f.state === "degraded" ? "warn" : f.state === "fresh" ? "ok" : "info";
  return { tone, text: stateText[f.state] };
}
