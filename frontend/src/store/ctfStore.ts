import { create } from "zustand";
import type { CtfSessionDetail, HintLevel } from "@/features/cybersecurity/ctf/ctfTypes";
import * as ctfService from "@/services/ctfService";
import { getApiErrorMessage } from "@/utils/apiError";

interface CtfState {
  session: CtfSessionDetail | null;
  isLoadingSession: boolean;
  isSendingMessage: boolean;
  isRequestingHint: boolean;
  isCompleting: boolean;
  error: string | null;

  loadSession: (sessionId: string) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  requestHint: (level: HintLevel, force?: boolean) => Promise<void>;
  complete: (flag?: string) => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

export const useCtfStore = create<CtfState>((set, get) => ({
  session: null,
  isLoadingSession: false,
  isSendingMessage: false,
  isRequestingHint: false,
  isCompleting: false,
  error: null,

  loadSession: async (sessionId) => {
    set({ isLoadingSession: true, error: null });
    try {
      const session = await ctfService.getSession(sessionId);
      set({ session, isLoadingSession: false });
    } catch (err) {
      set({
        isLoadingSession: false,
        error: getApiErrorMessage(err, "Unable to load this challenge session."),
      });
    }
  },

  sendMessage: async (message) => {
    const { session } = get();
    if (!session) return;

    set({ isSendingMessage: true, error: null });
    try {
      const now = new Date().toISOString();
      const response = await ctfService.sendMessage(session.session_id, message);
      set((state) =>
        state.session
          ? {
              session: {
                ...state.session,
                messages: [
                  ...state.session.messages,
                  { role: "user", content: message, created_at: now },
                  { role: "assistant", content: response, created_at: now },
                ],
              },
              isSendingMessage: false,
            }
          : { isSendingMessage: false }
      );
    } catch (err) {
      set({
        isSendingMessage: false,
        error: getApiErrorMessage(err, "Unable to reach the mentor. Please try again."),
      });
      throw err;
    }
  },

  requestHint: async (level, force = false) => {
    const { session } = get();
    if (!session) return;

    set({ isRequestingHint: true, error: null });
    try {
      const result = await ctfService.getHint(session.session_id, level, force);
      set((state) => {
        if (!state.session) return { isRequestingHint: false };
        const alreadyHave = state.session.hints.some((h) => h.level === level);
        const hints = alreadyHave
          ? state.session.hints
          : [
              ...state.session.hints,
              { level, content: result.content, requested_at: new Date().toISOString() },
            ];
        return {
          session: { ...state.session, hints, hints_used: result.hints_used },
          isRequestingHint: false,
        };
      });
    } catch (err) {
      set({
        isRequestingHint: false,
        error: getApiErrorMessage(err, "Unable to get a hint right now. Please try again."),
      });
    }
  },

  complete: async (flag) => {
    const { session } = get();
    if (!session) return;

    set({ isCompleting: true, error: null });
    try {
      await ctfService.completeSession(session.session_id, flag);
      set((state) =>
        state.session
          ? {
              session: {
                ...state.session,
                status: "completed",
                completed_at: new Date().toISOString(),
              },
              isCompleting: false,
            }
          : { isCompleting: false }
      );
    } catch (err) {
      set({
        isCompleting: false,
        error: getApiErrorMessage(err, "Unable to complete this session. Please try again."),
      });
    }
  },

  clearError: () => set({ error: null }),
  reset: () =>
    set({
      session: null,
      isLoadingSession: false,
      isSendingMessage: false,
      isRequestingHint: false,
      isCompleting: false,
      error: null,
    }),
}));
