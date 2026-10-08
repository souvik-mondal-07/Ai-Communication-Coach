import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { DailyPracticeState, Streak } from "@/types/dailyPractice";
import { DailyPracticeCardView } from "./DailyPracticeCard";
import { goalPercent, streakHeadline, streakHint } from "./dailyPracticeUtils";
import { StreakCard } from "./StreakCard";

const render = (node: React.ReactNode) => renderToStaticMarkup(<MemoryRouter>{node}</MemoryRouter>);

const streak = (over: Partial<Streak> = {}): Streak => ({
  current_streak: 7, longest_streak: 9, last_practice_date: "2026-10-07", total_active_days: 20,
  practiced_today: false, at_risk: true, timezone: "Asia/Kolkata", ...over,
});

const state = (over: Partial<DailyPracticeState> = {}): DailyPracticeState => ({
  enabled: true, rest_day: false, date: "2026-10-08", timezone: "Asia/Kolkata", streak: streak(), unread_notifications: 3,
  goal: { goal_minutes: 15, minutes_done: 8, tasks_total: 3, tasks_done: 1 },
  plan: {
    date: "2026-10-08", status: "in_progress", goal_minutes: 15, difficulty: "adaptive",
    focus: { title: "Strengthen SOC", topic: "SOC", basis: "performance" }, rationale: [], tasks: [],
    started_at: null, completed_at: null, completion: null, summary: null,
  },
  ...over,
});

const view = (data: DailyPracticeState | null, over = {}) =>
  render(<DailyPracticeCardView data={data} isLoading={false} error={null} onStart={vi.fn()} onRetry={vi.fn()} {...over} />);

describe("goalPercent", () => {
  it("clamps and rounds", () => {
    expect(goalPercent(8, 15)).toBe(53);
    expect(goalPercent(40, 15)).toBe(100);
    expect(goalPercent(-1, 15)).toBe(0);
    expect(goalPercent(5, 0)).toBe(0);
  });
});

describe("DailyPracticeCardView", () => {
  it("shows streak, goal, progress, recommendation and unread count from the API data", () => {
    const html = view(state());
    expect(html).toContain("7 Day Streak");
    expect(html).toContain("15 min goal");
    expect(html).toContain("Progress: 8 / 15 min");
    expect(html).toContain("Strengthen SOC");
    expect(html).toContain("Continue Practice");
    expect(html).toContain("Unread notifications:");
    expect(html).toMatch(/aria-valuenow="53"/);
  });
  it("offers Start Practice for a plan that has not begun", () => {
    const d = state();
    d.plan!.status = "pending";
    expect(view(d)).toContain("Start Practice");
  });
  it("links to the summary once completed instead of offering to start again", () => {
    const d = state();
    d.plan!.status = "completed";
    const html = view(d);
    expect(html).toContain("View today&#x27;s summary");
    expect(html).not.toContain("Start Practice");
  });
  it("has loading, error, disabled, rest-day states", () => {
    expect(view(null, { isLoading: true })).toContain("Loading today");
    const err = view(null, { error: "nope" });
    expect(err).toContain('role="alert"');
    expect(err).toContain("Retry");
    expect(view(state({ enabled: false, plan: null, goal: null }))).toContain("turned off");
    expect(view(state({ rest_day: true, plan: null, goal: null }))).toContain("rest day");
  });
  it("shows an action error without hiding the plan", () => {
    const html = view(state(), { actionError: "Unable to start" });
    expect(html).toContain("Unable to start");
    expect(html).toContain("Strengthen SOC");
  });
});

describe("Streak", () => {
  it("formats the headline and hints", () => {
    expect(streakHeadline(streak())).toBe("7 Day Streak");
    expect(streakHeadline(streak({ current_streak: 0 }))).toBe("No streak yet");
    expect(streakHint(streak({ practiced_today: true }))).toContain("practiced today");
    expect(streakHint(streak())).toContain("keep it going");
    expect(streakHint(streak({ current_streak: 0, total_active_days: 0 }))).toContain("start your streak");
  });
  it("states the counting rule and timezone", () => {
    const html = render(<StreakCard streak={streak()} />);
    expect(html).toContain("Longest");
    expect(html).toContain("Opening the app does not count");
    expect(html).toContain("Asia/Kolkata");
  });
});
