import { create } from "zustand";
import type {
  AnswerResult,
  Difficulty,
  PracticeCompleteResult,
  PublicQuestion,
} from "@/features/cybersecurity/cybersecurityTypes";
import * as cybersecurityService from "@/services/cybersecurityService";
import { getApiErrorMessage } from "@/utils/apiError";

interface PracticeState {
  sessionId: string | null;
  topicSlug: string | null;
  topicTitle: string | null;
  difficulty: Difficulty | null;
  questions: PublicQuestion[];
  currentQuestionIndex: number;
  /** Feedback for already-answered questions, keyed by question_id. */
  results: Record<string, AnswerResult>;
  finalResult: PracticeCompleteResult | null;
  isLoading: boolean;
  error: string | null;

  start: (topicSlug: string, difficulty?: Difficulty, questionCount?: number) => Promise<string>;
  submitCurrentAnswer: (answer: string) => Promise<void>;
  goToNextQuestion: () => void;
  complete: () => Promise<void>;
  reset: () => void;
  clearError: () => void;
}

const initialState = {
  sessionId: null as string | null,
  topicSlug: null as string | null,
  topicTitle: null as string | null,
  difficulty: null as Difficulty | null,
  questions: [] as PublicQuestion[],
  currentQuestionIndex: 0,
  results: {} as Record<string, AnswerResult>,
  finalResult: null as PracticeCompleteResult | null,
  isLoading: false,
  error: null as string | null,
};

export const usePracticeStore = create<PracticeState>((set, get) => ({
  ...initialState,

  start: async (topicSlug, difficulty, questionCount) => {
    set({ ...initialState, isLoading: true });
    try {
      const result = await cybersecurityService.startPractice({
        topicSlug,
        difficulty,
        questionCount,
      });
      set({
        sessionId: result.session_id,
        topicSlug: result.topic_slug,
        topicTitle: result.topic_title,
        difficulty: result.difficulty,
        questions: result.questions,
        currentQuestionIndex: 0,
        results: {},
        finalResult: null,
        isLoading: false,
      });
      return result.session_id;
    } catch (err) {
      set({
        isLoading: false,
        error: getApiErrorMessage(err, "Unable to generate practice questions. Please try again."),
      });
      throw err;
    }
  },

  submitCurrentAnswer: async (answer) => {
    const { sessionId, questions, currentQuestionIndex } = get();
    const question = questions[currentQuestionIndex];
    if (!sessionId || !question) return;

    set({ isLoading: true, error: null });
    try {
      const result = await cybersecurityService.submitAnswer({
        sessionId,
        questionId: question.question_id,
        answer,
      });
      set((state) => ({
        isLoading: false,
        results: { ...state.results, [question.question_id]: result },
      }));
    } catch (err) {
      set({
        isLoading: false,
        error: getApiErrorMessage(err, "Unable to evaluate your answer. Please try again."),
      });
      throw err;
    }
  },

  goToNextQuestion: () => {
    set((state) => ({
      currentQuestionIndex: Math.min(state.currentQuestionIndex + 1, state.questions.length - 1),
    }));
  },

  complete: async () => {
    const { sessionId } = get();
    if (!sessionId) return;

    set({ isLoading: true, error: null });
    try {
      const result = await cybersecurityService.completePractice(sessionId);
      set({ isLoading: false, finalResult: result });
    } catch (err) {
      set({
        isLoading: false,
        error: getApiErrorMessage(err, "Unable to complete the practice session. Please try again."),
      });
      throw err;
    }
  },

  reset: () => set({ ...initialState }),
  clearError: () => set({ error: null }),
}));
