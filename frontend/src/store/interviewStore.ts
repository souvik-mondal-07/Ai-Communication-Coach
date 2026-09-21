import { create } from "zustand";
import type { SendMessageOptions } from "@/features/voice/voiceTypes";
import * as interviewService from "@/services/interviewService";
import { getApiErrorMessage } from "@/utils/apiError";
import type { AnswerResult, InterviewSessionView } from "@/types/interview";

interface InterviewState {
  session: InterviewSessionView | null;
  /** Result of the most recent answer (its live evaluation, if feedback is on). */
  lastResult: AnswerResult | null;
  isLoadingSession: boolean;
  isSubmitting: boolean;
  isCompleting: boolean;
  error: string | null;

  loadSession: (sessionId: string) => Promise<void>;
  /** Rejects on failure so the caller can keep the user's answer for a retry. */
  submitAnswer: (answer: string, options?: SendMessageOptions) => Promise<void>;
  complete: () => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

export const useInterviewStore = create<InterviewState>((set, get) => ({
  session: null,
  lastResult: null,
  isLoadingSession: false,
  isSubmitting: false,
  isCompleting: false,
  error: null,

  loadSession: async (sessionId) => {
    set({ isLoadingSession: true, error: null, lastResult: null });
    try {
      const session = await interviewService.getInterview(sessionId);
      set({ session, isLoadingSession: false });
    } catch (err) {
      set({
        isLoadingSession: false,
        error: getApiErrorMessage(err, "Unable to load this interview."),
      });
    }
  },

  submitAnswer: async (answer, options) => {
    const { session } = get();
    if (!session) return;

    set({ isSubmitting: true, error: null });
    try {
      // The response carries the full updated session, so it is the single source of truth.
      const result = await interviewService.submitAnswer(session.session_id, answer, options);
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
      const updated = await interviewService.completeInterview(session.session_id);
      set({ session: updated, isCompleting: false });
    } catch (err) {
      set({
        isCompleting: false,
        error: getApiErrorMessage(err, "Couldn't end the interview. Please try again."),
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
      error: null,
    }),
}));
