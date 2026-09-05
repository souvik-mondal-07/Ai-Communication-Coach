import { useChatStore } from "@/store/chatStore";

/**
 * Placeholder hook exposing chat state to components.
 * Real send/receive logic is added with the AI Mentor feature.
 */
export function useChat() {
  const { messages } = useChatStore();
  return { messages };
}
