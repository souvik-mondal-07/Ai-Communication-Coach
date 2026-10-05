import axios from "axios";
import { create } from "zustand";
import type {
  AnswerResult,
  Difficulty,
  PracticeSessionConfig,
  PracticeSessionState,
} from "@/features/cybersecurity/cybersecurityTypes";
import { firstOpenIndex } from "@/features/cybersecurity/practice/practiceUtils";
import * as cybersecurityService from "@/services/cybersecurityService";
import { getApiErrorMessage } from "@/utils/apiError";

/**
 * Practice state. The server owns the session (questions, answers, hints, timer); this
 * store mirrors it so a page refresh can resume via `load(sessionId)`. Step 5 sessions
 * and Step 17 sessions share the same state shape.
 */

function errorCode(err: unknown): string | null {
  if (axios.isAxiosError(err)) {
    const code = (err.response?.data as { error_code?: unknown } | undefined)?.error_code;
    return typeof code === "string" ? code : null;
  }
  return null;
}

interface PracticeState {
  session: PracticeSessionState | null;
  /** Index (into session.questions) of the question on screen. */
  currentIndex: number;
  /** Unsent answer text per question id; kept here so a timer expiry can still save it. */
  drafts: Record<string, string>;
  /** Wall-clock time the timer reaches zero, or null when the session has no timer. */
  deadlineMs: number | null;
  isLoading: boolean;
  isSubmitting: boolean;
  isHintLoading: boolean;
  isAdvancing: boolean;
  error: string | null;

  /** Step 5 entry point (topic page): start a one-topic session and return its id. */
  start: (topicSlug: string, difficulty?: Difficulty, questionCount?: number) => Promise<string>;
  startSession: (config: PracticeSessionConfig) => Promise<string>;
  load: (sessionId: string) => Promise<void>;
  setDraft: (questionId: string, text: string) => void;
  submitCurrentAnswer: (answer: string) => Promise<void>;
  requestHint: () => Promise<void>;
  revealExplanation: () => Promise<void>;
  /** Next question (local navigation, or generating the next one), or finish after the last. */
  goToNext: () => Promise<void>;
  complete: () => Promise<void>;
  reset: () => void;
  clearError: () => void;
}

const initialState = {
  session: null as PracticeSessionState | null,
  currentIndex: 0,
  drafts: {} as Record<string, string>,
  deadlineMs: null as number | null,
  isLoading: false,
  isSubmitting: false,
  isHintLoading: false,
  isAdvancing: false,
  error: null as string | null,
};

function applyState(session: PracticeSessionState) {
  return {
    session,
    currentIndex: firstOpenIndex(session.questions),
    deadlineMs:
      session.remaining_seconds !== null && session.status === "in_progress"
        ? Date.now() + session.remaining_seconds * 1000
        : null,
  };
}

function patchQuestion(
  session: PracticeSessionState,
  questionId: string,
  patch: Partial<PracticeSessionState["questions"][number]>
): PracticeSessionState {
  return {
    ...session,
    questions: session.questions.map((q) => (q.question_id === questionId ? { ...q, ...patch } : q)),
  };
}

export const usePracticeStore = create<PracticeState>((set, get) => ({
  ...initialState,

  start: async (topicSlug, difficulty, questionCount) => {
    set({ ...initialState, isLoading: true });
    try {
      const started = await cybersecurityService.startPractice({ topicSlug, difficulty, questionCount });
      const session = await cybersecurityService.getPracticeSession(started.session_id);
      set({ ...applyState(session), isLoading: false });
      return started.session_id;
    } catch (err) {
      set({
        isLoading: false,
        error: getApiErrorMessage(err, "Unable to generate practice questions. Please try again."),
      });
      throw err;
    }
  },

  startSession: async (config) => {
    set({ ...initialState, isLoading: true });
    try {
      const session = await cybersecurityService.startPracticeSession(config);
      set({ ...applyState(session), isLoading: false });
      return session.session_id;
    } catch (err) {
      set({
        isLoading: false,
        error: getApiErrorMessage(err, "Unable to start practice. Please try again."),
      });
      throw err;
    }
  },

  load: async (sessionId) => {
    set({ isLoading: true, error: null });
    try {
      const session = await cybersecurityService.getPracticeSession(sessionId);
      set({ ...applyState(session), isLoading: false });
    } catch (err) {
      set({ isLoading: false, error: getApiErrorMessage(err, "Unable to load this practice session.") });
    }
  },

  setDraft: (questionId, text) => set((s) => ({ drafts: { ...s.drafts, [questionId]: text } })),

  submitCurrentAnswer: async (answer) => {
    const { session, currentIndex, isSubmitting } = get();
    const question = session?.questions[currentIndex];
    // One submission at a time, and never for an already-answered question.
    if (!session || !question || question.answered || isSubmitting) return;

    set({ isSubmitting: true, error: null });
    try {
      const result: AnswerResult = await cybersecurityService.submitAnswer({
        sessionId: session.session_id,
        questionId: question.question_id,
        answer,
      });
      set((s) => ({
        isSubmitting: false,
        session: s.session ? patchQuestion(s.session, question.question_id, { answered: true, result }) : s.session,
      }));
    } catch (err) {
      const code = errorCode(err);
      set({ isSubmitting: false, error: getApiErrorMessage(err, "Unable to evaluate your answer. Please try again.") });
      // Out of sync with the server (already answered / timer ended): refresh the real state.
      if (code === "ANSWER_ALREADY_SUBMITTED" || code === "SESSION_EXPIRED" || code === "SESSION_CLOSED") {
        await get().load(session.session_id);
      }
      throw err;
    }
  },

  requestHint: async () => {
    const { session, currentIndex, isHintLoading } = get();
    const question = session?.questions[currentIndex];
    if (!session || !question || question.answered || isHintLoading) return;

    set({ isHintLoading: true, error: null });
    try {
      const result = await cybersecurityService.requestPracticeHint({
        sessionId: session.session_id,
        questionId: question.question_id,
      });
      if (result.kind === "hint") {
        set((s) => ({
          isHintLoading: false,
          session: s.session
            ? patchQuestion(s.session, question.question_id, {
                hints_used: result.hints_used,
                hints: [...question.hints.slice(0, result.hint_number - 1), result.hint],
              })
            : s.session,
        }));
      } else {
        set({ isHintLoading: false });
      }
    } catch (err) {
      set({ isHintLoading: false, error: getApiErrorMessage(err, "Unable to get a hint right now.") });
    }
  },

  revealExplanation: async () => {
    const { session, currentIndex, isHintLoading } = get();
    const question = session?.questions[currentIndex];
    if (!session || !question || question.answered || isHintLoading) return;

    set({ isHintLoading: true, error: null });
    try {
      const result = await cybersecurityService.requestPracticeHint({
        sessionId: session.session_id,
        questionId: question.question_id,
        reveal: true,
      });
      if (result.kind === "explanation") {
        set((s) => ({
          isHintLoading: false,
          session: s.session
            ? patchQuestion(s.session, question.question_id, {
                answered: true,
                hints_used: result.hints_used,
                result: result.result,
              })
            : s.session,
        }));
      } else {
        set({ isHintLoading: false });
      }
    } catch (err) {
      set({ isHintLoading: false, error: getApiErrorMessage(err, "Unable to show the explanation right now.") });
    }
  },

  goToNext: async () => {
    const { session, currentIndex, isAdvancing } = get();
    if (!session || isAdvancing) return;

    if (currentIndex < session.questions.length - 1) {
      set({ currentIndex: currentIndex + 1 });
      return;
    }
    if (session.has_more_questions) {
      set({ isAdvancing: true, error: null });
      try {
        const { state } = await cybersecurityService.requestNextQuestion(session.session_id);
        set({ ...applyState(state), isAdvancing: false, currentIndex: state.questions.length - 1 });
      } catch (err) {
        set({ isAdvancing: false, error: getApiErrorMessage(err, "Unable to load the next question. Please try again.") });
        const code = errorCode(err);
        if (code === "SESSION_EXPIRED" || code === "SESSION_CLOSED") await get().load(session.session_id);
      }
      return;
    }
    try {
      await get().complete();
    } catch {
      // `complete` already recorded the error for the banner; the user can retry.
    }
  },

  complete: async () => {
    const { session } = get();
    if (!session) return;
    set({ isAdvancing: true, error: null });
    try {
      await cybersecurityService.completePractice(session.session_id);
      // Re-read so the summary and every question's result come from the saved session.
      const fresh = await cybersecurityService.getPracticeSession(session.session_id);
      set({ ...applyState(fresh), isAdvancing: false });
    } catch (err) {
      set({
        isAdvancing: false,
        error: getApiErrorMessage(err, "Unable to complete the practice session. Please try again."),
      });
      throw err;
    }
  },

  reset: () => set({ ...initialState }),
  clearError: () => set({ error: null }),
}));
