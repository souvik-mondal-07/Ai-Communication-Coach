import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DailyPracticeState, DailyTask } from "@/types/dailyPractice";

vi.mock("@/services/dailyPracticeService", () => ({
  getDailyPractice: vi.fn(), startDailyPractice: vi.fn(), regenerateDailyPractice: vi.fn(),
  completeDailyPractice: vi.fn(), linkTaskSession: vi.fn(), getStreak: vi.fn(),
}));
vi.mock("@/features/dailyPractice/dailyPracticeLauncher", () => ({ launchTask: vi.fn() }));

import { launchTask } from "@/features/dailyPractice/dailyPracticeLauncher";
import * as svc from "@/services/dailyPracticeService";
import { useNotificationStore } from "./notificationStore";
import { useDailyPracticeStore } from "./dailyPracticeStore";

const task = (id: DailyTask["kind"], status: DailyTask["status"]): DailyTask => ({
  task_id: id, kind: id, title: id, description: "", why: [], est_minutes: 5, route: "/x", config: {},
  status, session_id: null, score: null, minutes: null,
});
const state = (tasks: DailyTask[], unread = 2): DailyPracticeState => ({
  enabled: true, rest_day: false, date: "2026-10-08", timezone: "UTC", unread_notifications: unread,
  streak: { current_streak: 1, longest_streak: 1, last_practice_date: null, total_active_days: 1, practiced_today: false, at_risk: false, timezone: "UTC" },
  goal: { goal_minutes: 15, minutes_done: 0, tasks_total: tasks.length, tasks_done: 0 },
  plan: { date: "2026-10-08", status: "pending", goal_minutes: 15, difficulty: "beginner",
    focus: { title: "f", topic: "t", basis: "profile" }, rationale: [], tasks, started_at: null, completed_at: null, completion: null, summary: null },
});

beforeEach(() => {
  vi.clearAllMocks();
  useDailyPracticeStore.getState().reset();
  useNotificationStore.getState().reset();
});

describe("dailyPracticeStore", () => {
  it("loads today's practice and syncs the unread badge", async () => {
    vi.mocked(svc.getDailyPractice).mockResolvedValue(state([task("cybersecurity", "pending")], 6));
    await useDailyPracticeStore.getState().load();
    expect(useDailyPracticeStore.getState().data?.plan?.tasks).toHaveLength(1);
    expect(useNotificationStore.getState().unreadCount).toBe(6);
  });
  it("surfaces a load error and clears it on retry", async () => {
    vi.mocked(svc.getDailyPractice).mockRejectedValueOnce(new Error("x"));
    await useDailyPracticeStore.getState().load();
    expect(useDailyPracticeStore.getState().error).toBeTruthy();
    vi.mocked(svc.getDailyPractice).mockResolvedValue(state([task("cybersecurity", "pending")]));
    await useDailyPracticeStore.getState().load();
    expect(useDailyPracticeStore.getState().error).toBeNull();
  });
  it("start opens the first unfinished task", async () => {
    vi.mocked(svc.startDailyPractice).mockResolvedValue(state([task("cybersecurity", "completed"), task("communication", "pending")]));
    vi.mocked(launchTask).mockResolvedValue("/communication/c1");
    expect(await useDailyPracticeStore.getState().start()).toBe("/communication/c1");
    expect(vi.mocked(launchTask).mock.calls[0][0].task_id).toBe("communication");
  });
  it("start reports a failure instead of throwing", async () => {
    vi.mocked(svc.startDailyPractice).mockRejectedValue(new Error("x"));
    expect(await useDailyPracticeStore.getState().start()).toBeNull();
    expect(useDailyPracticeStore.getState().actionError).toBeTruthy();
    expect(useDailyPracticeStore.getState().isActing).toBe(false);
  });
  it("complete replaces the data with the finished plan", async () => {
    const done = state([task("cybersecurity", "completed")]);
    done.plan!.status = "completed";
    vi.mocked(svc.completeDailyPractice).mockResolvedValue(done);
    await useDailyPracticeStore.getState().complete();
    expect(useDailyPracticeStore.getState().data?.plan?.status).toBe("completed");
  });
  it("complete failure keeps the existing plan and shows an error", async () => {
    useDailyPracticeStore.setState({ data: state([task("cybersecurity", "pending")]) });
    vi.mocked(svc.completeDailyPractice).mockRejectedValue(new Error("x"));
    await useDailyPracticeStore.getState().complete();
    expect(useDailyPracticeStore.getState().data?.plan?.status).toBe("pending");
    expect(useDailyPracticeStore.getState().actionError).toBeTruthy();
  });
});
