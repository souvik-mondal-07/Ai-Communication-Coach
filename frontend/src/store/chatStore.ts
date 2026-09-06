import { create } from "zustand";
import type { MentorLevel, MentorMode } from "@/features/mentor/mentorTypes";
import { sendMentorMessage } from "@/services/mentorService";
import type { ChatMessage } from "@/types/chat";
import { getApiErrorMessage } from "@/utils/apiError";

// Only the most recent turns are sent as context. The backend independently
// bounds this too (see MentorService.CONTEXT_WINDOW) — this just keeps the
// request itself from growing unbounded over a long session.
const MAX_HISTORY_TURNS = 20;

function makeId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  mode: MentorMode;
  level: MentorLevel;

  setMode: (mode: MentorMode) => void;
  setLevel: (level: MentorLevel) => void;
  /** Sends `content` to the mentor. Rethrows on failure so the input UI can
   *  restore the typed text; the failed error message is also stored in
   *  `error` for the banner UI. */
  sendMessage: (content: string) => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  error: null,
  mode: "learn",
  level: "intermediate",

  setMode: (mode) => set({ mode }),
  setLevel: (level) => set({ level }),

  sendMessage: async (content) => {
    const trimmed = content.trim();
    if (!trimmed || get().isLoading) return;

    const userMessage: ChatMessage = {
      id: makeId(),
      role: "user",
      content: trimmed,
      createdAt: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    const history = get()
      .messages.slice(-MAX_HISTORY_TURNS)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const { response, mode, level } = await sendMentorMessage({
        message: trimmed,
        mode: get().mode,
        level: get().level,
        conversationHistory: history,
      });

      const assistantMessage: ChatMessage = {
        id: makeId(),
        role: "assistant",
        content: response,
        createdAt: new Date().toISOString(),
      };

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        isLoading: false,
        mode,
        level,
      }));
    } catch (err) {
      const message = getApiErrorMessage(
        err,
        "Unable to reach the AI mentor. Please try again."
      );
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  clearError: () => set({ error: null }),

  reset: () => set({ messages: [], isLoading: false, error: null }),
}));
