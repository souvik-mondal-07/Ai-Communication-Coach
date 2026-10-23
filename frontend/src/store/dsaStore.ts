import { create } from "zustand";
import * as svc from "@/services/dsaService";
import { apiErrorCode } from "@/features/dsa/dsaMeta";
import type { DsaProgress, DsaResult, DsaSession, Recommendations, SelfVerdict, SessionQuestion, SessionRequest, Syllabus } from "@/types/dsa";
import { getApiErrorMessage } from "@/utils/apiError";

type Load = "idle" | "loading" | "ready" | "error";

interface DsaState {
  syllabus: Syllabus | null;
  syllabusStatus: Load;
  syllabusError: string | null;

  session: DsaSession | null;
  sessionStatus: Load;
  sessionError: string | null;
  /** Difference between the server's clock and this device's (ms), so the countdown follows the server. */
  clockOffsetMs: number;
  currentIndex: number;
  isStarting: boolean;
  startError: string | null;
  isSubmitting: boolean;
  answerError: string | null;
  /** Unsaved code the user is typing, per question id. */
  drafts: Record<string, string>;
  savingCode: string | null;
  /** Set when the server has ended the session (time up / already submitted): the page should show the result. */
  ended: boolean;

  result: DsaResult | null;
  resultStatus: Load;
  resultError: string | null;

  progress: DsaProgress | null;
  recommendations: Recommendations | null;
  progressStatus: Load;
  progressError: string | null;

  loadSyllabus: () => Promise<void>;
  startSession: (request: SessionRequest) => Promise<string | null>;
  loadSession: (id: string) => Promise<void>;
  goTo: (index: number) => void;
  selectAnswer: (questionId: string, index: number | null) => Promise<void>;
  setDraft: (questionId: string, code: string) => void;
  saveCode: (questionId: string, opts?: { reveal?: boolean }) => Promise<void>;
  toggleMark: (questionId: string) => Promise<void>;
  submit: () => Promise<DsaResult | null>;
  loadResult: (id: string) => Promise<void>;
  assessCode: (questionId: string, verdict: SelfVerdict) => Promise<void>;
  loadProgress: () => Promise<void>;
  clearAnswerError: () => void;
  reset: () => void;
}

const EMPTY = {
  syllabus: null, syllabusStatus: "idle" as Load, syllabusError: null,
  session: null, sessionStatus: "idle" as Load, sessionError: null, clockOffsetMs: 0, currentIndex: 0, isStarting: false, startError: null,
  isSubmitting: false, answerError: null, drafts: {} as Record<string, string>, savingCode: null, ended: false,
  result: null, resultStatus: "idle" as Load, resultError: null,
  progress: null, recommendations: null, progressStatus: "idle" as Load, progressError: null,
};

/** Seconds spent on each question this visit, kept outside React state (it changes every second and drives no UI). */
const spent = new Map<string, number>();
let viewing: { id: string; since: number } | null = null;

function bankTime(now = Date.now()): void {
  if (viewing) {
    spent.set(viewing.id, (spent.get(viewing.id) ?? 0) + Math.max(0, Math.round((now - viewing.since) / 1000)));
    viewing = { ...viewing, since: now };
  }
}

function startViewing(id: string | undefined): void {
  bankTime();
  viewing = id ? { id, since: Date.now() } : null;
}

function patchQuestion(session: DsaSession, id: string, patch: Partial<SessionQuestion>): DsaSession {
  return { ...session, questions: session.questions.map((q) => (q.question_id === id ? { ...q, ...patch } : q)) };
}

const isEnded = (code: string | null) => code === "SESSION_EXPIRED" || code === "SESSION_COMPLETED";
const firstOpenIndex = (s: DsaSession) => s.questions.findIndex((q) => q.selected_index === null && !q.code_answer);

export const useDsaStore = create<DsaState>((set, get) => ({
  ...EMPTY,

  loadSyllabus: async () => {
    set({ syllabusStatus: "loading", syllabusError: null });
    try {
      set({ syllabus: await svc.getSyllabus(), syllabusStatus: "ready" });
    } catch (err) {
      set({ syllabusStatus: "error", syllabusError: getApiErrorMessage(err, "Unable to load the DSA syllabus.") });
    }
  },

  startSession: async (request) => {
    if (get().isStarting) return null;
    set({ isStarting: true, startError: null });
    try {
      const session = await svc.createSession(request);
      spent.clear();
      set({ isStarting: false, session, sessionStatus: "ready", sessionError: null, currentIndex: 0, ended: false, answerError: null, result: null, drafts: {}, clockOffsetMs: Date.parse(session.server_time) - Date.now() });
      startViewing(session.questions[0]?.question_id);
      return session.session_id;
    } catch (err) {
      set({ isStarting: false, startError: getApiErrorMessage(err, "Unable to start the session.") });
      return null;
    }
  },

  loadSession: async (id) => {
    set({ sessionStatus: "loading", sessionError: null, ended: false, answerError: null });
    try {
      const session = await svc.getSession(id);
      // Resuming after a refresh: land on the first unanswered question so no progress is lost or repeated.
      const firstOpen = firstOpenIndex(session);
      const drafts: Record<string, string> = {};
      for (const q of session.questions) if (q.code_answer) drafts[q.question_id] = q.code_answer;
      spent.clear();
      set({ session, drafts, sessionStatus: "ready", currentIndex: firstOpen >= 0 ? firstOpen : 0, ended: session.status === "completed", clockOffsetMs: Date.parse(session.server_time) - Date.now() });
      startViewing(session.status === "completed" ? undefined : session.questions[firstOpen >= 0 ? firstOpen : 0]?.question_id);
    } catch (err) {
      set({ sessionStatus: "error", sessionError: getApiErrorMessage(err, "Unable to load this practice session.") });
    }
  },

  goTo: (index) => {
    const { session, currentIndex, drafts } = get();
    if (!session || index < 0 || index >= session.questions.length) return;
    // Leaving a coding question with unsaved edits saves them first, so navigating never loses work.
    const leaving = session.questions[currentIndex];
    if (leaving?.interaction === "code" && !leaving.locked && drafts[leaving.question_id] !== undefined && drafts[leaving.question_id] !== (leaving.code_answer ?? "")) {
      void get().saveCode(leaving.question_id);
    }
    startViewing(session.questions[index].question_id);
    set({ currentIndex: index });
  },

  selectAnswer: async (questionId, index) => {
    const { session } = get();
    const q = session?.questions.find((x) => x.question_id === questionId);
    if (!session || !q || q.interaction !== "mcq" || q.locked || get().ended || session.status !== "in_progress") return;
    const before = { selected_index: q.selected_index, marked_for_review: q.marked_for_review };
    bankTime();
    set({ session: patchQuestion(session, questionId, { selected_index: index }), answerError: null });
    try {
      const saved = await svc.saveAnswer(session.session_id, questionId, { selected_index: index, marked_for_review: before.marked_for_review, time_spent_seconds: spent.get(questionId) ?? 0 });
      const current = get().session;
      if (current) set({ session: patchQuestion(current, questionId, { locked: saved.locked, feedback: saved.feedback }) });
    } catch (err) {
      const code = apiErrorCode(err);
      if (isEnded(code)) { set({ ended: true, answerError: getApiErrorMessage(err, "This session has ended.") }); return; }
      const current = get().session;
      if (current) set({ session: patchQuestion(current, questionId, before) });
      set({ answerError: getApiErrorMessage(err, "Your answer could not be saved. Please try again.") });
    }
  },

  setDraft: (questionId, code) => set((s) => ({ drafts: { ...s.drafts, [questionId]: code } })),

  saveCode: async (questionId, opts) => {
    const { session, drafts } = get();
    const q = session?.questions.find((x) => x.question_id === questionId);
    if (!session || !q || q.interaction !== "code" || q.locked || get().ended || session.status !== "in_progress") return;
    const code = drafts[questionId] ?? q.code_answer ?? "";
    bankTime();
    set({ savingCode: questionId, answerError: null });
    try {
      const saved = await svc.saveAnswer(session.session_id, questionId, { code, reveal: opts?.reveal ?? false, marked_for_review: q.marked_for_review, time_spent_seconds: spent.get(questionId) ?? 0 });
      const current = get().session;
      if (current) set({ session: patchQuestion(current, questionId, { code_answer: saved.code_answer, locked: saved.locked, feedback: saved.feedback }) });
    } catch (err) {
      const errCode = apiErrorCode(err);
      if (isEnded(errCode)) set({ ended: true, answerError: getApiErrorMessage(err, "This session has ended.") });
      else set({ answerError: getApiErrorMessage(err, "Your code could not be saved. It is still in the editor - try again.") });
    } finally {
      set({ savingCode: null });
    }
  },

  toggleMark: async (questionId) => {
    const { session, drafts } = get();
    const q = session?.questions.find((x) => x.question_id === questionId);
    if (!session || !q || get().ended || session.status !== "in_progress") return;
    const next = !q.marked_for_review;
    set({ session: patchQuestion(session, questionId, { marked_for_review: next }), answerError: null });
    try {
      const body = q.interaction === "code"
        ? { code: drafts[questionId] ?? q.code_answer ?? "", marked_for_review: next, time_spent_seconds: spent.get(questionId) ?? 0 }
        : { selected_index: q.selected_index, marked_for_review: next, time_spent_seconds: spent.get(questionId) ?? 0 };
      await svc.saveAnswer(session.session_id, questionId, body);
    } catch (err) {
      const code = apiErrorCode(err);
      if (isEnded(code)) { set({ ended: true, answerError: getApiErrorMessage(err, "This session has ended.") }); return; }
      const current = get().session;
      if (current) set({ session: patchQuestion(current, questionId, { marked_for_review: !next }) });
      set({ answerError: getApiErrorMessage(err, "Could not update the review mark.") });
    }
  },

  submit: async () => {
    const { session, isSubmitting, currentIndex, drafts } = get();
    if (!session || isSubmitting) return get().result; // a second click or the auto-submit racing the button does nothing
    set({ isSubmitting: true, answerError: null });
    try {
      // Persist unsaved code on the current question before finalising.
      const cur = session.questions[currentIndex];
      if (cur?.interaction === "code" && !cur.locked && drafts[cur.question_id] !== undefined && drafts[cur.question_id] !== (cur.code_answer ?? "")) {
        try { await svc.saveAnswer(session.session_id, cur.question_id, { code: drafts[cur.question_id], marked_for_review: cur.marked_for_review, time_spent_seconds: spent.get(cur.question_id) ?? 0 }); } catch { /* the submit below reports any real problem */ }
      }
      const result = await svc.submitSession(session.session_id);
      startViewing(undefined);
      set({ result, resultStatus: "ready", isSubmitting: false, ended: true });
      return result;
    } catch (err) {
      set({ isSubmitting: false, answerError: getApiErrorMessage(err, "Could not submit. Your answers are saved - try again.") });
      return null;
    }
  },

  loadResult: async (id) => {
    set({ resultStatus: "loading", resultError: null });
    try {
      set({ result: await svc.getResult(id), resultStatus: "ready" });
    } catch (err) {
      set({ resultStatus: "error", resultError: getApiErrorMessage(err, "Unable to load this result.") });
    }
  },

  assessCode: async (questionId, verdict) => {
    const { result } = get();
    if (!result) return;
    try {
      await svc.setSelfAssessment(result.session_id, questionId, verdict);
      const current = get().result;
      if (current) set({ result: { ...current, questions: current.questions.map((q) => (q.question_id === questionId ? { ...q, self_assessment: verdict } : q)) } });
    } catch (err) {
      set({ resultError: getApiErrorMessage(err, "Could not save your self-assessment.") });
    }
  },

  loadProgress: async () => {
    set({ progressStatus: "loading", progressError: null });
    try {
      const [progress, recommendations] = await Promise.all([svc.getProgress(), svc.getRecommendations()]);
      set({ progress, recommendations, progressStatus: "ready" });
    } catch (err) {
      set({ progressStatus: "error", progressError: getApiErrorMessage(err, "Unable to load your DSA progress.") });
    }
  },

  clearAnswerError: () => set({ answerError: null }),

  reset: () => {
    spent.clear();
    viewing = null;
    set({ ...EMPTY });
  },
}));
