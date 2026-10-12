import { describe, expect, it } from "vitest";
import type { OverviewSessionCounts } from "@/types/progress";
import { firstName, formatScore, greetingFor, plural, totalCompleted, totalStarted } from "./dashboardUtils";

const counts: OverviewSessionCounts = {
  practice_sessions: { total: 5, completed: 4 },
  ctf_sessions: { total: 2, completed: 1 },
  communication_sessions: { total: 0, completed: 0 },
  interview_sessions: { total: 3, completed: 3 },
  pressure_sessions: { total: 1, completed: 0 },
};

describe("dashboardUtils", () => {
  it("picks a greeting by hour", () => {
    expect(greetingFor(2)).toBe("Working late");
    expect(greetingFor(9)).toBe("Good morning");
    expect(greetingFor(12)).toBe("Good afternoon");
    expect(greetingFor(18)).toBe("Good evening");
  });
  it("uses the first name with a fallback", () => {
    expect(firstName("Asha Verma")).toBe("Asha");
    expect(firstName("  ")).toBe("there");
    expect(firstName(undefined)).toBe("there");
  });
  it("formats scores and refuses to invent missing ones", () => {
    expect(formatScore(77.6)).toBe("78/100");
    expect(formatScore(0)).toBe("0/100");
    expect(formatScore(null)).toBeNull();
    expect(formatScore(undefined)).toBeNull();
    expect(formatScore(NaN)).toBeNull();
  });
  it("sums real session counts", () => {
    expect(totalCompleted(counts)).toBe(8);
    expect(totalStarted(counts)).toBe(11);
  });
  it("pluralizes", () => {
    expect(plural(1, "session")).toBe("1 session");
    expect(plural(0, "session")).toBe("0 sessions");
  });
});

import { buildSkillAxes, mergeTrends, percent, relativeTime } from "./dashboardUtils";
import type { ProgressOverview } from "@/types/progress";

describe("percent", () => {
  it("rounds and clamps, and is safe for zero or bad totals", () => {
    expect(percent(3, 5)).toBe(60);
    expect(percent(1, 3)).toBe(33);
    expect(percent(0, 0)).toBe(0);
    expect(percent(5, 0)).toBe(0);
    expect(percent(9, 3)).toBe(100);
    expect(percent(NaN, 3)).toBe(0);
  });
});

describe("relativeTime", () => {
  const now = new Date("2026-10-13T12:00:00Z").getTime();
  it("formats minutes, hours and days", () => {
    expect(relativeTime("2026-10-13T11:59:50Z", now)).toBe("Just now");
    expect(relativeTime("2026-10-13T11:30:00Z", now)).toBe("30 minutes ago");
    expect(relativeTime("2026-10-13T10:00:00Z", now)).toBe("2 hours ago");
    expect(relativeTime("2026-10-12T12:00:00Z", now)).toBe("1 day ago");
    expect(relativeTime("not a date", now)).toBe("");
  });
});

describe("buildSkillAxes", () => {
  it("uses only backend values and leaves missing dimensions null", () => {
    const o = {
      cybersecurity_performance: { categories_practiced: 1, average_score: 70.4 },
      communication_performance: { overall_score: 65, confidence_score: 55 },
      interview_performance: null,
      pressure_performance: null,
    } as unknown as ProgressOverview;
    const v = Object.fromEntries(buildSkillAxes(o).map((a) => [a.key, a.value]));
    expect(v).toEqual({ security: 70, communication: 65, interview: null, confidence: 55, pressure: null });
  });
});

describe("mergeTrends", () => {
  it("aligns series by period and leaves gaps as null", () => {
    const pt = (period: string, average_score: number) => ({ period, average_score, count: 1 });
    const empty = { points: [], trend: "insufficient_data" as const };
    const rows = mergeTrends({
      technical: { points: [pt("2026-10-02", 50), pt("2026-10-01", 40)], trend: "improving" },
      communication: { points: [pt("2026-10-02", 30)], trend: "stable" },
      interview: empty, pressure: empty, overall: empty,
    });
    expect(rows.map((r) => r.period)).toEqual(["2026-10-01", "2026-10-02"]);
    expect(rows[0]).toMatchObject({ technical: 40, communication: null });
    expect(rows[1]).toMatchObject({ technical: 50, communication: 30 });
  });
});
