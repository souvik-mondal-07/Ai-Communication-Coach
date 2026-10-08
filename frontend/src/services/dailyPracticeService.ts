import { api } from "@/services/api";
import type { DailyPracticeState, Streak, TaskKind } from "@/types/dailyPractice";

/** Client for `/api/v1/daily-practice` (Step 19). */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export async function getDailyPractice(): Promise<DailyPracticeState> {
  const { data } = await api.get<ApiEnvelope<DailyPracticeState>>("/daily-practice");
  return data.data;
}

export async function getStreak(): Promise<Streak> {
  const { data } = await api.get<ApiEnvelope<Streak>>("/daily-practice/streak");
  return data.data;
}

export async function startDailyPractice(): Promise<DailyPracticeState> {
  const { data } = await api.post<ApiEnvelope<DailyPracticeState>>("/daily-practice/start");
  return data.data;
}

/** Attach a session started through an existing module to today's task. */
export async function linkTaskSession(taskId: TaskKind, sessionId: string): Promise<DailyPracticeState> {
  const { data } = await api.post<ApiEnvelope<DailyPracticeState>>(
    `/daily-practice/tasks/${encodeURIComponent(taskId)}/link`,
    { session_id: sessionId }
  );
  return data.data;
}

export async function regenerateDailyPractice(): Promise<DailyPracticeState> {
  const { data } = await api.post<ApiEnvelope<DailyPracticeState>>("/daily-practice/regenerate");
  return data.data;
}

export async function completeDailyPractice(): Promise<DailyPracticeState> {
  const { data } = await api.post<ApiEnvelope<DailyPracticeState>>("/daily-practice/complete");
  return data.data;
}
