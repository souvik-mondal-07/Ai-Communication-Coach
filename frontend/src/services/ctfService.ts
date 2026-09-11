import { api } from "@/services/api";
import type {
  ChallengeCategory,
  CtfDifficulty,
  CtfSessionDetail,
  CtfSessionSummary,
  HintLevel,
  Platform,
} from "@/features/cybersecurity/ctf/ctfTypes";

/**
 * Client for the CTF & Practical Lab Mentor endpoints. Talks only to
 * FastAPI (`/api/v1/ctf/...`) — the AI never runs commands or accesses any
 * target; it only reasons about what the user tells it. This file never
 * calls Gemini or any AI provider directly.
 */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface CreateSessionPayload {
  platform: Platform;
  category: ChallengeCategory;
  difficulty: CtfDifficulty;
  title: string;
  description: string;
  user_notes?: string;
}

export async function createSession(
  payload: CreateSessionPayload
): Promise<{ session_id: string; status: string }> {
  const { data } = await api.post<ApiEnvelope<{ session_id: string; status: string }>>(
    "/ctf/sessions",
    payload
  );
  return data.data;
}

export async function getSessions(params?: {
  page?: number;
  limit?: number;
}): Promise<{ sessions: CtfSessionSummary[]; page: number; limit: number; total: number }> {
  const { data } = await api.get<
    ApiEnvelope<{ sessions: CtfSessionSummary[]; page: number; limit: number; total: number }>
  >("/ctf/sessions", { params });
  return data.data;
}

export async function getSession(sessionId: string): Promise<CtfSessionDetail> {
  const { data } = await api.get<ApiEnvelope<CtfSessionDetail>>(
    `/ctf/sessions/${encodeURIComponent(sessionId)}`
  );
  return data.data;
}

export async function sendMessage(sessionId: string, message: string): Promise<string> {
  const { data } = await api.post<ApiEnvelope<{ response: string }>>(
    `/ctf/sessions/${encodeURIComponent(sessionId)}/chat`,
    { message }
  );
  return data.data.response;
}

export async function getHint(
  sessionId: string,
  level: HintLevel,
  force = false
): Promise<{ level: HintLevel; content: string; hints_used: number }> {
  const { data } = await api.get<
    ApiEnvelope<{ level: HintLevel; content: string; hints_used: number }>
  >(`/ctf/sessions/${encodeURIComponent(sessionId)}/hint`, { params: { level, force } });
  return data.data;
}

export async function completeSession(
  sessionId: string,
  flag?: string
): Promise<{ status: string }> {
  const { data } = await api.post<ApiEnvelope<{ status: string }>>(
    `/ctf/sessions/${encodeURIComponent(sessionId)}/complete`,
    { flag: flag || undefined }
  );
  return data.data;
}
