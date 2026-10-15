import { describe, expect, it } from "vitest";
import { describeFreshness, formatPublished, safeExternalUrl } from "./newsMeta";
import type { NewsFreshness } from "@/types/news";

const NOW = new Date("2026-10-15T12:00:00Z");
const fresh = (over: Partial<NewsFreshness> = {}): NewsFreshness => ({
  state: "fresh", last_successful_refresh_at: "2026-10-15T11:40:00Z", last_attempt_at: null, refreshing: false,
  refresh_interval_minutes: 30, sources_ok: 8, sources_failed: 0, message: null, ...over,
});

describe("safeExternalUrl", () => {
  it("accepts plain http(s) URLs", () => {
    expect(safeExternalUrl("https://www.cisa.gov/news/x")).toBe("https://www.cisa.gov/news/x");
    expect(safeExternalUrl("http://example.com/a")).toBe("http://example.com/a");
  });
  it.each(["javascript:alert(1)", "data:text/html,<script>1</script>", "vbscript:x", "file:///etc/passwd", "//evil.com", "/relative", "", "not a url", "https://user:pw@example.com/x"])(
    "rejects %s", (bad) => expect(safeExternalUrl(bad)).toBeNull()
  );
  it("rejects non-strings", () => {
    for (const v of [null, undefined, 42, {}, []]) expect(safeExternalUrl(v)).toBeNull();
  });
});

describe("formatPublished", () => {
  it("is relative for the last week and a date after that", () => {
    expect(formatPublished("2026-10-15T11:59:30Z", NOW)).toBe("just now");
    expect(formatPublished("2026-10-15T11:30:00Z", NOW)).toBe("30 min ago");
    expect(formatPublished("2026-10-15T11:00:00Z", NOW)).toBe("1 hour ago");
    expect(formatPublished("2026-10-15T07:00:00Z", NOW)).toBe("5 hours ago");
    expect(formatPublished("2026-10-13T12:00:00Z", NOW)).toBe("2 days ago");
    expect(formatPublished("2026-09-01T12:00:00Z", NOW)).toBe("1 Sept 2026");
  });
  it("returns null instead of inventing a date", () => {
    for (const v of [null, undefined, "", "yesterday", "2026-13-99"]) expect(formatPublished(v as string | null, NOW)).toBeNull();
  });
  it("shows a date, not 'in the future', for clock-skewed timestamps", () => {
    expect(formatPublished("2026-10-20T12:00:00Z", NOW)).toBe("20 Oct 2026");
  });
});

describe("describeFreshness", () => {
  it("says when it was last updated and how often it checks, and never claims real time", () => {
    const { tone, text } = describeFreshness(fresh(), NOW);
    expect(tone).toBe("ok");
    expect(text).toContain("Last updated 20 min ago");
    expect(text).toContain("about every 30 minutes");
  });
  it("warns honestly when the live refresh is failing", () => {
    const { tone, text } = describeFreshness(fresh({ state: "degraded", last_successful_refresh_at: "2026-10-15T05:00:00Z" }), NOW);
    expect(tone).toBe("warn");
    expect(text).toMatch(/cached articles/i);
    expect(text).toMatch(/failing/i);
  });
  it.each(["fresh", "stale", "degraded", "empty"] as const)("never uses 'live' or 'real-time' wording (%s)", (state) => {
    const { text } = describeFreshness(fresh({ state }), NOW);
    expect(text).not.toMatch(/real.?time|\blive news\b|up to the minute/i);
  });
  it("handles an empty cache that is being fetched", () => {
    expect(describeFreshness(fresh({ state: "empty", last_successful_refresh_at: null, refreshing: true }), NOW).text).toMatch(/Fetching/);
  });
});
