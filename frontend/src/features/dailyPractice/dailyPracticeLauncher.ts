import * as communicationService from "@/services/communicationService";
import * as dailyPracticeService from "@/services/dailyPracticeService";
import * as interviewService from "@/services/interviewService";
import { usePracticeStore } from "@/store/practiceStore";
import type { DailyTask } from "@/types/dailyPractice";
import type { PracticeSessionConfig } from "@/features/cybersecurity/cybersecurityTypes";

/**
 * Starts (or resumes) a daily-practice task through the module that already owns that kind
 * of practice -- there is no separate practice engine. Returns the route to open.
 */

/** Where an already-started session lives. */
export function sessionRoute(kind: DailyTask["kind"], sessionId: string): string {
  const id = encodeURIComponent(sessionId);
  if (kind === "cybersecurity") return `/cybersecurity/practice/${id}`;
  if (kind === "communication") return `/communication/${id}`;
  return `/interview/${id}`;
}

/** Route to continue a task, or null if it has no session yet. */
export function resumeRoute(task: DailyTask): string | null {
  return task.session_id ? sessionRoute(task.kind, task.session_id) : null;
}

export function toPracticeConfig(task: DailyTask): PracticeSessionConfig {
  const c = task.config as Record<string, unknown>;
  return {
    mode: c.mode as PracticeSessionConfig["mode"],
    category: (c.category as string | null) ?? null,
    difficulty: c.difficulty as PracticeSessionConfig["difficulty"],
    questionType: (c.question_type as PracticeSessionConfig["questionType"]) ?? "mixed",
    questionCount: Number(c.question_count) || 3,
  };
}

async function startNewSession(task: DailyTask): Promise<string> {
  const c = task.config as Record<string, unknown>;
  if (task.kind === "cybersecurity") {
    return usePracticeStore.getState().startSession(toPracticeConfig(task));
  }
  if (task.kind === "communication") {
    const started = await communicationService.startSession(
      String(c.scenario_id),
      c.difficulty as Parameters<typeof communicationService.startSession>[1]
    );
    return started.session_id;
  }
  const started = await interviewService.startInterview({
    interviewType: c.interview_type as Parameters<typeof interviewService.startInterview>[0]["interviewType"],
    difficulty: c.difficulty as Parameters<typeof interviewService.startInterview>[0]["difficulty"],
    questionCount: Number(c.question_count) || 5,
    mode: (c.mode as "text" | "voice") ?? "text",
    revealFeedback: true,
  });
  return started.session_id;
}

/** Resume if a session is already linked, otherwise start one and link it to the task. */
export async function launchTask(task: DailyTask): Promise<string> {
  const existing = resumeRoute(task);
  if (existing && task.status === "in_progress") return existing;

  const sessionId = await startNewSession(task);
  try {
    await dailyPracticeService.linkTaskSession(task.task_id, sessionId);
  } catch {
    // The session itself is fine and still counts as practice; only the checklist link is missing.
  }
  return sessionRoute(task.kind, sessionId);
}
