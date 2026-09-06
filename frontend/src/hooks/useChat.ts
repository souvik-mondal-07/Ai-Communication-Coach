import { useChatStore } from "@/store/chatStore";

/**
 * Thin hook wrapping the chat store so components never call the store
 * (or mentorService) directly.
 */
export function useChat() {
  const messages = useChatStore((s) => s.messages);
  const isLoading = useChatStore((s) => s.isLoading);
  const error = useChatStore((s) => s.error);
  const mode = useChatStore((s) => s.mode);
  const level = useChatStore((s) => s.level);
  const setMode = useChatStore((s) => s.setMode);
  const setLevel = useChatStore((s) => s.setLevel);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const clearError = useChatStore((s) => s.clearError);
  const reset = useChatStore((s) => s.reset);

  return {
    messages,
    isLoading,
    error,
    mode,
    level,
    setMode,
    setLevel,
    sendMessage,
    clearError,
    reset,
  };
}
