import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DailyTask } from "@/types/dailyPractice";

vi.mock("@/services/communicationService", () => ({ startSession: vi.fn() }));
vi.mock("@/services/interviewService", () => ({ startInterview: vi.fn() }));
vi.mock("@/services/dailyPracticeService", () => ({ linkTaskSession: vi.fn() }));
vi.mock("@/store/practiceStore", () => ({ usePracticeStore: { getState: vi.fn() } }));

import * as communication from "@/services/communicationService";
import * as dailyPractice from "@/services/dailyPracticeService";
import * as interview from "@/services/interviewService";
import { usePracticeStore } from "@/store/practiceStore";
import { launchTask, resumeRoute, sessionRoute, toPracticeConfig } from "./dailyPracticeLauncher";

const task = (over: Partial<DailyTask> = {}): DailyTask => ({
  task_id: "cybersecurity", kind: "cybersecurity", title: "Strengthen SOC", description: "d", why: [], est_minutes: 9,
  route: "/cybersecurity/practice", status: "pending", session_id: null, score: null, minutes: null,
  config: { mode: "topic", category: "SOC", difficulty: "adaptive", question_type: "mixed", question_count: 3 },
  ...over,
});

const startSession = vi.fn();
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(usePracticeStore.getState).mockReturnValue({ startSession } as never);
  vi.mocked(dailyPractice.linkTaskSession).mockResolvedValue({} as never);
});

describe("routes", () => {
  it("maps each kind to the module that owns its session", () => {
    expect(sessionRoute("cybersecurity", "abc")).toBe("/cybersecurity/practice/abc");
    expect(sessionRoute("communication", "abc")).toBe("/communication/abc");
    expect(sessionRoute("interview", "abc")).toBe("/interview/abc");
  });
  it("resumes only when a session is linked", () => {
    expect(resumeRoute(task())).toBeNull();
    expect(resumeRoute(task({ session_id: "s9", status: "in_progress" }))).toBe("/cybersecurity/practice/s9");
  });
  it("converts the plan config to the practice engine's config", () => {
    expect(toPracticeConfig(task())).toEqual({
      mode: "topic", category: "SOC", difficulty: "adaptive", questionType: "mixed", questionCount: 3,
    });
  });
});

describe("launchTask", () => {
  it("starts a cybersecurity session through the existing practice store, then links it", async () => {
    startSession.mockResolvedValue("s1");
    expect(await launchTask(task())).toBe("/cybersecurity/practice/s1");
    expect(startSession).toHaveBeenCalledWith(expect.objectContaining({ mode: "topic", category: "SOC", questionCount: 3 }));
    expect(dailyPractice.linkTaskSession).toHaveBeenCalledWith("cybersecurity", "s1");
  });
  it("starts a communication scenario with the planned scenario and difficulty", async () => {
    vi.mocked(communication.startSession).mockResolvedValue({ session_id: "c1" } as never);
    const t = task({ task_id: "communication", kind: "communication", config: { scenario_id: "sc1", difficulty: "beginner" } });
    expect(await launchTask(t)).toBe("/communication/c1");
    expect(communication.startSession).toHaveBeenCalledWith("sc1", "beginner");
    expect(dailyPractice.linkTaskSession).toHaveBeenCalledWith("communication", "c1");
  });
  it("starts an interview with the planned type and length", async () => {
    vi.mocked(interview.startInterview).mockResolvedValue({ session_id: "i1" } as never);
    const t = task({
      task_id: "interview", kind: "interview",
      config: { interview_type: "technical", difficulty: "beginner", question_count: 5, mode: "text" },
    });
    expect(await launchTask(t)).toBe("/interview/i1");
    expect(interview.startInterview).toHaveBeenCalledWith(
      expect.objectContaining({ interviewType: "technical", questionCount: 5, mode: "text" })
    );
  });
  it("resumes an in-progress task instead of starting a duplicate session", async () => {
    expect(await launchTask(task({ status: "in_progress", session_id: "s5" }))).toBe("/cybersecurity/practice/s5");
    expect(startSession).not.toHaveBeenCalled();
    expect(dailyPractice.linkTaskSession).not.toHaveBeenCalled();
  });
  it("still opens the session when only the link call fails", async () => {
    startSession.mockResolvedValue("s2");
    vi.mocked(dailyPractice.linkTaskSession).mockRejectedValue(new Error("offline"));
    expect(await launchTask(task())).toBe("/cybersecurity/practice/s2");
  });
  it("propagates a failed session start", async () => {
    startSession.mockRejectedValue(new Error("boom"));
    await expect(launchTask(task())).rejects.toThrow("boom");
    expect(dailyPractice.linkTaskSession).not.toHaveBeenCalled();
  });
});
