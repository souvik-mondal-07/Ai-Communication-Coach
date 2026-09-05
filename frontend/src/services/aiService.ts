import { api } from "@/services/api";

/**
 * Minimal client for the AI engine's test endpoint.
 *
 * This talks only to FastAPI (`/api/v1/ai/chat`) — never to Gemini or any
 * other AI provider directly. The full Mentor chat UI is built in a later
 * step on top of this same function.
 */

export type ChatRole = "user" | "assistant";

export interface ChatHistoryMessage {
  role: ChatRole;
  content: string;
}

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

interface ChatResponseData {
  response: string;
}

/**
 * Send a message (with optional prior conversation turns) to the AI mentor
 * engine and return its reply. Requires the caller to already be
 * authenticated — the Authorization header is attached automatically by
 * the shared `api` client.
 */
export async function sendMessage(
  message: string,
  conversationHistory: ChatHistoryMessage[] = []
): Promise<string> {
  const { data } = await api.post<ApiEnvelope<ChatResponseData>>("/ai/chat", {
    message,
    conversation_history: conversationHistory,
  });
  return data.data.response;
}
