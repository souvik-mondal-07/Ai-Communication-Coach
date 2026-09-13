import { create } from "zustand";
import type { SessionDetail } from "@/features/communication/communicationTypes";
import * as communicationService from "@/services/communicationService";
import { getApiErrorMessage } from "@/utils/apiError";

interface CommunicationState {
  session: SessionDetail | null;
  isLoadingSession: boolean;
  isSendingMessage: boolean;
  isCompleting: boolean;
  error: string | null;

  loadSession: (sessionId: string) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  complete: () => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

export const useCommunicationStore = create<CommunicationState>((set, get) => ({
  session: null,
  isLoadingSession: false,
  isSendingMessage: false,
  isCompleting: false,
  error: null,

  loadSession: async (sessionId) => {
    set({ isLoadingSession: true, error: null });
    try {
      const session = await communicationService.getSession(sessionId);
      set({ session, isLoadingSession: false });
    } catch (err) {
      set({
        isLoadingSession: false,
        error: getApiErrorMessage(err, "Unable to load this practice session."),
      });
    }
  },

  sendMessage: async (message) => {
    const { session } = get();
    if (!session) return;

    set({ isSendingMessage: true, error: null });
    try {
      const now = new Date().toISOString();
      const result = await communicationService.sendMessage(session.session_id, message);
      set((state) =>
        state.session
          ? {
              session: {
                ...state.session,
                messages: [
                  ...state.session.messages,
                  { role: "user", content: message, timestamp: now },
                  { role: "assistant", content: result.reply, timestamp: now },
                ],
              },
              isSendingMessage: false,
            }
          : { isSendingMessage: false }
      );
    } catch (err) {
      set({
        isSendingMessage: false,
        error: getApiErrorMessage(err, "Unable to reach the AI. Please try again."),
      });
      throw err;
    }
  },

  complete: async () => {
    const { session } = get();
    if (!session) return;

    set({ isCompleting: true, error: null });
    try {
      const result = await communicationService.completeSession(session.session_id);
      set((state) =>
        state.session
          ? {
              session: {
                ...state.session,
                status: "completed",
                completed_at: new Date().toISOString(),
                evaluation: result.evaluation,
              },
              isCompleting: false,
            }
          : { isCompleting: false }
      );
    } catch (err) {
      set({
        isCompleting: false,
        error: getApiErrorMessage(err, "Unable to evaluate this session. Please try again."),
      });
    }
  },

  clearError: () => set({ error: null }),
  reset: () =>
    set({ session: null, isLoadingSession: false, isSendingMessage: false, isCompleting: false, error: null }),
}));
