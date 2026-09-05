import { create } from "zustand";
import type { ChatMessage } from "@/types/chat";

/**
 * Placeholder chat store.
 *
 * Step 1 only establishes the shape of this store so the future AI Mentor
 * chat feature can plug in without a rewrite. No AI logic is implemented yet.
 */
interface ChatState {
  messages: ChatMessage[];
}

export const useChatStore = create<ChatState>(() => ({
  messages: [],
}));
