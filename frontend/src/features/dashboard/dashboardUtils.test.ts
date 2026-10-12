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
