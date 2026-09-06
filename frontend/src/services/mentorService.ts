import { api } from "@/services/api";
import type { MentorLevel, MentorMode } from "@/features/mentor/mentorTypes";

/**
 * Client for the Mentor chat endpoint. Talks only to FastAPI
 * (`/api/v1/mentor/chat`) — never to Gemini or any other AI provider
 * directly. Never put raw Axios calls in components; call this instead.
 */

export interface MentorHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface MentorChatPayload {
  message: string;
  mode: MentorMode;
  level: MentorLevel;
  conversationHistory: MentorHistoryMessage[];
}

export interface MentorChatResult {
  response: string;
  mode: MentorMode;
  level: MentorLevel;
}

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

/**
 * Send a message (with mode, level, and prior conversation turns) to the
 * mentor and return its reply. Requires the caller to already be
 * authenticated — the Authorization header is attached automatically by
 * the shared `api` client.
 */
export async function sendMentorMessage(
  payload: MentorChatPayload
): Promise<MentorChatResult> {
  const { data } = await api.post<ApiEnvelope<MentorChatResult>>("/mentor/chat", {
    message: payload.message,
    mode: payload.mode,
    level: payload.level,
    conversation_history: payload.conversationHistory,
  });
  return data.data;
}
