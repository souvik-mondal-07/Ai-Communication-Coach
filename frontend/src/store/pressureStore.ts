import { create } from "zustand";
import type { SendMessageOptions } from "@/features/voice/voiceTypes";
import * as pressureService from "@/services/pressureService";
import { getApiErrorMessage } from "@/utils/apiError";
import type { PressureResponseResult, PressureSessionView, SelfReportedDifficulty } from "@/types/pressure";

interface SubmitExtras extends SendMessageOptions {
  timedOut?: boolean;
  responseDurationSeconds?: number;
}

interface PressureState {
  session: PressureSessionView | null;
  lastResult: PressureResponseResult | null;
  isLoadingSession: boolean;
  isSubmitting: boolean;
  isCompleting: boolean;
  isSavingSelfReport: boolean;
  error: string | null;

  loadSession: (sessionId: string) => Promise<void>;
  /** Rejects on failure so the caller can keep the user's answer for a retry. */
  submitAnswer: (answer: string, options?: SubmitExtras) => Promise<void>;
  complete: () => Promise<void>;
  submitSelfReport: (difficulty: SelfReportedDifficulty, note?: string) => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

export const usePressureStore = create<PressureState>((set, get) => ({
  session: null,
  lastResult: null,
  isLoadingSession: false,
  isSubmitting: false,
  isCompleting: false,
  isSavingSelfReport: false,
  error: null,

  loadSession: async (sessionId) => {
    set({ isLoadingSession: true, error: null, lastResult: null });
    try {
      const session = await pressureService.getPressureSession(sessionId);
      set({ session, isLoadingSession: false });
    } catch (err) {
      set({
        isLoadingSession: false,
        error: getApiErrorMessage(err, "Unable to load this pressure training session."),
      });
    }
  },

  submitAnswer: async (answer, options) => {
    const { session } = get();
    if (!session) return;

    set({ isSubmitting: true, error: null });
    try {
      // The response carries the full updated session, so it is the single source of truth.
      const result = await pressureService.submitPressureResponse(session.session_id, answer, options);
      set({ session: result.session, lastResult: result, isSubmitting: false });
    } catch (err) {
      set({
        isSubmitting: false,
        error: getApiErrorMessage(err, "Couldn't submit your answer. Please try again."),
      });
      throw err;
    }
  },

  complete: async () => {
    const { session } = get();
    if (!session) return;

    set({ isCompleting: true, error: null });
    try {
      const updated = await pressureService.completePressureSession(session.session_id);
      set({ session: updated, isCompleting: false });
    } catch (err) {
      set({
        isCompleting: false,
        error: getApiErrorMessage(err, "Couldn't end the session. Please try again."),
      });
    }
  },

  submitSelfReport: async (difficulty, note) => {
    const { session } = get();
    if (!session) return;

    set({ isSavingSelfReport: true, error: null });
    try {
      const updated = await pressureService.submitSelfReport(session.session_id, difficulty, note);
      set({ session: updated, isSavingSelfReport: false });
    } catch (err) {
      set({
        isSavingSelfReport: false,
        error: getApiErrorMessage(err, "Couldn't save how the session felt. Please try again."),
      });
    }
  },

  clearError: () => set({ error: null }),
  reset: () =>
    set({
      session: null,
      lastResult: null,
      isLoadingSession: false,
      isSubmitting: false,
      isCompleting: false,
      isSavingSelfReport: false,
      error: null,
    }),
}));
