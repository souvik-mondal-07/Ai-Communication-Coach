import { describe, expect, it } from "vitest";
import type { TrendSeries } from "@/types/analytics";
import {
  bandColor,
  buildChartRows,
  changeToneClass,
  formatChange,
  formatPeriod,
  formatScore,
  hasChartData,
} from "./analyticsUtils";

const series = (points: [string, number | null][]): TrendSeries => ({
  label: "x",
  higher_is_better: true,
  direction: "stable",
  points: points.map(([period, value]) => ({ period, value, samples: 1 })),
});

describe("analyticsUtils", () => {
  it("renders missing data as N/A, never 0", () => {
    expect(formatScore(null)).toBe("N/A");
    expect(formatScore(undefined)).toBe("N/A");
    expect(formatScore(0)).toBe("0");
    expect(formatScore(81, "%")).toBe("81%");
    expect(formatChange(null)).toBe("N/A");
    expect(formatChange(13)).toBe("+13");
    expect(formatChange(-4)).toBe("-4");
    expect(formatChange(0)).toBe("0");
  });

  it("merges series by period and leaves gaps as null", () => {
    const rows = buildChartRows(
      { technical: series([["2026-10-01", 60], ["2026-10-03", 70]]), confidence: series([["2026-10-03", 55]]) },
      ["technical", "confidence"],
    );
    expect(rows).toEqual([
      { period: "2026-10-01", technical: 60, confidence: null },
      { period: "2026-10-03", technical: 70, confidence: 55 },
    ]);
  });

  it("detects whether any chart data exists", () => {
    expect(hasChartData({ a: series([]) }, ["a", "missing"])).toBe(false);
    expect(hasChartData({ a: series([["2026-10-01", 1]]) }, ["a"])).toBe(true);
  });

  it("formats day, month and unknown periods", () => {
    expect(formatPeriod("2026-10-05")).toBe("Oct 5");
    expect(formatPeriod("2026-01")).toBe("Jan 2026");
    expect(formatPeriod("weird")).toBe("weird");
  });

  it("maps change labels and scores to tones/colours", () => {
    expect(changeToneClass("Improving")).toBe("text-signal");
    expect(changeToneClass("Needs attention")).toBe("text-danger");
    expect(changeToneClass(null)).toBe("text-text-muted");
    expect(bandColor(null)).toBe("#6c7889");
    expect(bandColor(80)).toBe("#35d0ba");
    expect(bandColor(59)).toBe("#e5484d");
    expect(bandColor(70)).toBe("#f5a623");
  });
});
