import { describe, expect, it } from "vitest";
import { DEFAULT_FILTERS, PAGE_SIZE, dateBounds, formatElapsed, hasActiveFilters, isInvalidCustomRange, isActivityType, toQuery } from "@/features/history/historyMeta";

const NOW = new Date(2026, 9, 2, 15, 30, 0); // local time: 2 Oct 2026 15:30

describe("dateBounds", () => {
  it("has no bounds for all time", () => {
    expect(dateBounds({ range: "all", customStart: "", customEnd: "" }, NOW)).toEqual({});
  });

  it("'today' starts at local midnight", () => {
    const { start, end } = dateBounds({ range: "today", customStart: "", customEnd: "" }, NOW);
    expect(new Date(start!).getTime()).toBe(new Date(2026, 9, 2, 0, 0, 0).getTime());
    expect(end).toBeUndefined();
  });

  it("presets look back a fixed number of days", () => {
    const week = dateBounds({ range: "7d", customStart: "", customEnd: "" }, NOW).start!;
    const month = dateBounds({ range: "30d", customStart: "", customEnd: "" }, NOW).start!;
    expect(NOW.getTime() - new Date(week).getTime()).toBe(7 * 86_400_000);
    expect(NOW.getTime() - new Date(month).getTime()).toBe(30 * 86_400_000);
  });

  it("a custom range covers the whole of both local days", () => {
    const { start, end } = dateBounds({ range: "custom", customStart: "2026-09-01", customEnd: "2026-09-30" }, NOW);
    expect(new Date(start!).getTime()).toBe(new Date(2026, 8, 1, 0, 0, 0, 0).getTime());
    expect(new Date(end!).getTime()).toBe(new Date(2026, 8, 30, 23, 59, 59, 999).getTime());
  });

  it("ignores an incomplete or malformed custom range", () => {
    expect(dateBounds({ range: "custom", customStart: "", customEnd: "" }, NOW)).toEqual({ start: undefined, end: undefined });
    expect(dateBounds({ range: "custom", customStart: "garbage", customEnd: "" }, NOW).start).toBeUndefined();
  });
});

describe("filters", () => {
  it("detects an inverted custom range only", () => {
    const base = { ...DEFAULT_FILTERS, range: "custom" as const };
    expect(isInvalidCustomRange({ ...base, customStart: "2026-10-05", customEnd: "2026-10-01" })).toBe(true);
    expect(isInvalidCustomRange({ ...base, customStart: "2026-10-01", customEnd: "2026-10-05" })).toBe(false);
    expect(isInvalidCustomRange({ ...base, customStart: "2026-10-01", customEnd: "" })).toBe(false);
    expect(isInvalidCustomRange({ ...DEFAULT_FILTERS, customStart: "2026-10-05", customEnd: "2026-10-01" })).toBe(false);
  });

  it("builds a query without empty parameters and never a user id", () => {
    const q = toQuery({ ...DEFAULT_FILTERS, search: "  linux  ", type: "interview" }, 3);
    expect(q).toMatchObject({ type: "interview", search: "linux", page: 3, limit: PAGE_SIZE, sort: "newest" });
    expect(Object.keys(q)).not.toContain("user_id");
    const bare = toQuery(DEFAULT_FILTERS, 1);
    expect(bare.type).toBeUndefined();
    expect(bare.search).toBeUndefined();
  });

  it("reports active search/date filters but not the type tab", () => {
    expect(hasActiveFilters(DEFAULT_FILTERS)).toBe(false);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, type: "ctf" })).toBe(false);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, search: "x" })).toBe(true);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, range: "7d" })).toBe(true);
  });

  it("only accepts real activity types in the URL", () => {
    expect(isActivityType("interview")).toBe(true);
    expect(isActivityType("mentor")).toBe(false);
    expect(isActivityType(undefined)).toBe(false);
  });
});

describe("formatElapsed", () => {
  it("formats seconds, minutes and hours", () => {
    expect(formatElapsed(45)).toBe("45 sec");
    expect(formatElapsed(18 * 60)).toBe("18 min");
    expect(formatElapsed(3600)).toBe("1 hr");
    expect(formatElapsed(3600 + 20 * 60)).toBe("1 hr 20 min");
  });
});
