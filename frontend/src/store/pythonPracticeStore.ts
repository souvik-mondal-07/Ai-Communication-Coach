import { create } from "zustand";
import * as svc from "@/services/pythonPracticeService";
import { apiErrorCode } from "@/features/python-practice/pythonPracticeMeta";
import type {
  CheckOutcome, GradeResult, HistoryPage, PyProgress, PyResult, PySession, Feedback, Recommendations, SessionQuestion, SessionRequest, Syllabus,
} from "@/types/pythonPractice";
import { getApiErrorMessage } from "@/utils/apiError";

type Load = "idle" | "loading" | "ready" | "error";

interface PyState {
  syllabus: Syllabus | null;
  syllabusStatus: Load;
  syllabusError: string | null;

  history: HistoryPage | null;
  historyStatus: Load;
  historyError: string | null;

  session: PySession | null;
  sessionStatus: Load;
  sessionError: string | null;
  /** Difference between the server's clock and this device's (ms), so the countdown follows the server. */
  clockOffsetMs: number;
  currentIndex: number;
  isStarting: boolean;
  startError: string | null;
  isSubmitting: boolean;
  answerError: string | null;
  /** Unsaved code / short answers the user is typing, per question id. */
  drafts: Record<string, string>;
  /** Latest trial run (visible example tests) and latest submission outcome per question (display only; the server decides correctness). */
  runs: Record<string, GradeResult>;
  checkResults: Record<string, CheckOutcome>;
  busy: Record<string, "run" | "check" | "reveal" | "hint" | undefined>;
  /** Set when the server has ended the session (time up / already submitted): the page should show the result. */
  ended: boolean;

  result: PyResult | null;
  resultStatus: Load;
  resultError: string | null;

  progress: PyProgress | null;
  recommendations: Recommendations | null;
  progressStatus: Load;
  progressError: string | null;

  loadSyllabus: () => Promise<void>;
  loadHistory: () => Promise<void>;
  startSession: (request: SessionRequest) => Promise<string | null>;
  loadSession: (id: string) => Promise<void>;
  goTo: (index: number) => void;
  selectAnswer: (questionId: string, index: number | null) => Promise<void>;
  setDraft: (questionId: string, text: string) => void;
  saveDraft: (questionId: string) => Promise<void>;
  runCode: (questionId: string) => Promise<void>;
  checkAnswer: (questionId: string) => Promise<void>;
  revealSolution: (questionId: string) => Promise<void>;
  requestHint: (questionId: string) => Promise<void>;
  toggleMark: (questionId: string) => Promise<void>;
  submit: () => Promise<PyResult | null>;
  loadResult: (id: string) => Promise<void>;
  loadProgress: () => Promise<void>;
  clearAnswerError: () => void;
  reset: () => void;
}

const EMPTY = {
  syllabus: null, syllabusStatus: "idle" as Load, syllabusError: null,
  history: null, historyStatus: "idle" as Load, historyError: null,
  session: null, sessionStatus: "idle" as Load, sessionError: null, clockOffsetMs: 0, currentIndex: 0, isStarting: false, startError: null,
  isSubmitting: false, answerError: null, drafts: {} as Record<string, string>, runs: {} as Record<string, GradeResult>, checkResults: {} as Record<string, CheckOutcome>,
  busy: {} as Record<string, "run" | "check" | "reveal" | "hint" | undefined>, ended: false,
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

function patchQuestion(session: PySession, id: string, patch: Partial<SessionQuestion>): PySession {
  return { ...session, questions: session.questions.map((q) => (q.question_id === id ? { ...q, ...patch } : q)) };
}

const isEnded = (code: string | null) => code === "SESSION_EXPIRED" || code === "SESSION_COMPLETED";
const answerText = (q: SessionQuestion) => (q.interaction === "code" ? q.code_answer : q.text_answer) ?? "";
/** A typed answer with edits that are not saved yet. An untouched starter template is not an answer, so it is never auto-saved. */
const hasUnsaved = (q: SessionQuestion, draft: string | undefined) =>
  draft !== undefined && draft !== answerText(q) && !(q.interaction === "code" && !answerText(q) && draft === q.code_spec?.starter);
const firstOpenIndex = (s: PySession) => s.questions.findIndex((q) => q.selected_index === null && !q.code_answer && !q.text_answer);

export const usePythonPracticeStore = create<PyState>((set, get) => {
  const setBusy = (id: string, value: "run" | "check" | "reveal" | "hint" | undefined) => set((s) => ({ busy: { ...s.busy, [id]: value } }));
  const lookup = (id: string) => {
    const { session } = get();
    const q = session?.questions.find((x) => x.question_id === id);
    return session && q ? { session, q } : null;
  };
  const handleEnded = (err: unknown): boolean => {
    if (isEnded(apiErrorCode(err))) {
      set({ ended: true, answerError: getApiErrorMessage(err, "This session has ended.") });
      return true;
    }
    return false;
  };

  return {
    ...EMPTY,

    loadSyllabus: async () => {
      set({ syllabusStatus: "loading", syllabusError: null });
      try {
        set({ syllabus: await svc.getSyllabus(), syllabusStatus: "ready" });
      } catch (err) {
        set({ syllabusStatus: "error", syllabusError: getApiErrorMessage(err, "Unable to load the Python syllabus.") });
      }
    },

    loadHistory: async () => {
      set({ historyStatus: "loading", historyError: null });
      try {
        set({ history: await svc.getHistory(1, 10), historyStatus: "ready" });
      } catch (err) {
        set({ historyStatus: "error", historyError: getApiErrorMessage(err, "Unable to load your session history.") });
      }
    },

    startSession: async (request) => {
      if (get().isStarting) return null;
      set({ isStarting: true, startError: null });
      try {
        const session = await svc.createSession(request);
        spent.clear();
        set({
          isStarting: false, session, sessionStatus: "ready", sessionError: null, currentIndex: 0, ended: false, answerError: null, result: null,
          drafts: {}, runs: {}, checkResults: {}, busy: {}, clockOffsetMs: Date.parse(session.server_time) - Date.now(),
        });
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
        const firstOpen = firstOpenIndex(session);
        const drafts: Record<string, string> = {};
        for (const q of session.questions) if (answerText(q)) drafts[q.question_id] = answerText(q);
        spent.clear();
        set({
          session, drafts, runs: {}, checkResults: {}, busy: {}, sessionStatus: "ready", currentIndex: firstOpen >= 0 ? firstOpen : 0,
          ended: session.status === "completed", clockOffsetMs: Date.parse(session.server_time) - Date.now(),
        });
        startViewing(session.status === "completed" ? undefined : session.questions[firstOpen >= 0 ? firstOpen : 0]?.question_id);
      } catch (err) {
        set({ sessionStatus: "error", sessionError: getApiErrorMessage(err, "Unable to load this practice session.") });
      }
    },

    goTo: (index) => {
      const { session, currentIndex, drafts } = get();
      if (!session || index < 0 || index >= session.questions.length) return;
      // Leaving a typed answer with unsaved edits saves them first, so navigating never loses work.
      const leaving = session.questions[currentIndex];
      if (leaving && leaving.interaction !== "mcq" && !leaving.locked && hasUnsaved(leaving, drafts[leaving.question_id])) {
        void get().saveDraft(leaving.question_id);
      }
      startViewing(session.questions[index].question_id);
      set({ currentIndex: index });
    },

    selectAnswer: async (questionId, index) => {
      const found = lookup(questionId);
      if (!found || found.q.interaction !== "mcq" || found.q.locked || get().ended || found.session.status !== "in_progress") return;
      const { session, q } = found;
      const before = { selected_index: q.selected_index, marked_for_review: q.marked_for_review };
      bankTime();
      set({ session: patchQuestion(session, questionId, { selected_index: index }), answerError: null });
      try {
        const saved = await svc.saveAnswer(session.session_id, questionId, { selected_index: index, marked_for_review: before.marked_for_review, time_spent_seconds: spent.get(questionId) ?? 0 });
        const current = get().session;
        if (current) set({ session: patchQuestion(current, questionId, { locked: saved.locked, feedback: saved.feedback }) });
      } catch (err) {
        if (handleEnded(err)) return;
        const current = get().session;
        if (current) set({ session: patchQuestion(current, questionId, before) });
        set({ answerError: getApiErrorMessage(err, "Your answer could not be saved. Please try again.") });
      }
    },

    setDraft: (questionId, text) => set((s) => ({ drafts: { ...s.drafts, [questionId]: text } })),

    saveDraft: async (questionId) => {
      const found = lookup(questionId);
      if (!found || found.q.interaction === "mcq" || found.q.locked || get().ended || found.session.status !== "in_progress") return;
      const { session, q } = found;
      const text = get().drafts[questionId] ?? answerText(q);
      bankTime();
      try {
        await svc.saveAnswer(session.session_id, questionId, {
          ...(q.interaction === "code" ? { code: text } : { text }), marked_for_review: q.marked_for_review, time_spent_seconds: spent.get(questionId) ?? 0,
        });
        const current = get().session;
        if (current) set({ session: patchQuestion(current, questionId, q.interaction === "code" ? { code_answer: text || null } : { text_answer: text || null }) });
      } catch (err) {
        if (!handleEnded(err)) set({ answerError: getApiErrorMessage(err, "Your answer could not be saved. It is still in the editor, so try again.") });
      }
    },

    runCode: async (questionId) => {
      const found = lookup(questionId);
      if (!found || get().busy[questionId] || found.q.locked || get().ended) return;
      const code = get().drafts[questionId] ?? "";
      if (!code.trim()) {
        set({ answerError: "Write some code first." });
        return;
      }
      setBusy(questionId, "run");
      try {
        const out = await svc.runCode(found.session.session_id, questionId, code);
        const current = get().session;
        set((s) => ({
          runs: { ...s.runs, [questionId]: out.result },
          session: current ? patchQuestion(current, questionId, { runs: found.q.runs + 1, code_answer: code }) : s.session,
          answerError: out.result.verdict === "runner_error" ? out.result.message : null,
        }));
      } catch (err) {
        if (!handleEnded(err)) set({ answerError: getApiErrorMessage(err, "The code could not be run. Please try again in a moment.") });
      } finally {
        setBusy(questionId, undefined);
      }
    },

    checkAnswer: async (questionId) => {
      const found = lookup(questionId);
      if (!found || found.q.locked || get().busy[questionId] || get().ended) return;
      const { session, q } = found;
      const text = get().drafts[questionId] ?? "";
      if (!text.trim()) {
        set({ answerError: q.interaction === "code" ? "Write your solution first." : "Type an answer first." });
        return;
      }
      setBusy(questionId, "check");
      bankTime();
      try {
        const out = await svc.checkAnswer(session.session_id, questionId, { ...(q.interaction === "code" ? { code: text } : { text }), time_spent_seconds: spent.get(questionId) ?? 0 });
        const current = get().session;
        set((s) => ({
          checkResults: { ...s.checkResults, [questionId]: out },
          session: current
            ? patchQuestion(current, questionId, {
              locked: out.locked, feedback: out.feedback as Feedback | null, checks: out.checks, can_reveal: out.can_reveal ?? false,
              last_check: out.result ? { verdict: out.result.verdict, passed: out.result.passed, total: out.result.total } : null,
              ...(q.interaction === "code" ? { code_answer: text } : { text_answer: text }),
            })
            : s.session,
        }));
      } catch (err) {
        if (!handleEnded(err)) set({ answerError: getApiErrorMessage(err, "The answer could not be checked. Please try again.") });
      } finally {
        setBusy(questionId, undefined);
      }
    },

    revealSolution: async (questionId) => {
      const found = lookup(questionId);
      if (!found || found.q.locked || get().busy[questionId]) return;
      setBusy(questionId, "reveal");
      try {
        const out = await svc.revealSolution(found.session.session_id, questionId);
        const current = get().session;
        if (current) set({ session: patchQuestion(current, questionId, { locked: true, feedback: out.feedback }) });
      } catch (err) {
        if (!handleEnded(err)) set({ answerError: getApiErrorMessage(err, "The solution could not be revealed.") });
      } finally {
        setBusy(questionId, undefined);
      }
    },

    requestHint: async (questionId) => {
      const found = lookup(questionId);
      if (!found || found.q.locked || get().busy[questionId] || found.q.hints_used >= found.q.hints_total) return;
      setBusy(questionId, "hint");
      try {
        const out = await svc.requestHint(found.session.session_id, questionId);
        const current = get().session;
        if (current) {
          // Using every hint unlocks the reference solution on the server (practice sessions only), so mirror that rule for the button.
          const allSeen = out.hint_number >= out.hints_total;
          const unlocked = found.q.interaction === "code" && found.session.immediate_feedback && !found.session.exam_mode && (found.q.can_reveal || allSeen);
          set({ session: patchQuestion(current, questionId, { hints: out.hints, hints_used: out.hint_number, hints_total: out.hints_total, can_reveal: unlocked }) });
        }
      } catch (err) {
        if (!handleEnded(err)) set({ answerError: getApiErrorMessage(err, "No hint is available right now.") });
      } finally {
        setBusy(questionId, undefined);
      }
    },

    toggleMark: async (questionId) => {
      const found = lookup(questionId);
      if (!found || get().ended || found.session.status !== "in_progress") return;
      const { session, q } = found;
      const next = !q.marked_for_review;
      set({ session: patchQuestion(session, questionId, { marked_for_review: next }), answerError: null });
      try {
        const base = { marked_for_review: next, time_spent_seconds: spent.get(questionId) ?? 0 };
        const draft = get().drafts[questionId] ?? answerText(q);
        const body = q.interaction === "mcq" ? { selected_index: q.selected_index, ...base } : q.interaction === "code" ? { code: draft, ...base } : { text: draft, ...base };
        await svc.saveAnswer(session.session_id, questionId, body);
      } catch (err) {
        if (handleEnded(err)) return;
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
        // Persist unsaved typed answers on the current question before finalising (the server grades the last saved text).
        const cur = session.questions[currentIndex];
        if (cur && cur.interaction !== "mcq" && !cur.locked && hasUnsaved(cur, drafts[cur.question_id])) {
          try {
            await svc.saveAnswer(session.session_id, cur.question_id, {
              ...(cur.interaction === "code" ? { code: drafts[cur.question_id] } : { text: drafts[cur.question_id] }), marked_for_review: cur.marked_for_review, time_spent_seconds: spent.get(cur.question_id) ?? 0,
            });
          } catch { /* the submit below reports any real problem */ }
        }
        const result = await svc.submitSession(session.session_id);
        startViewing(undefined);
        set({ result, resultStatus: "ready", isSubmitting: false, ended: true });
        return result;
      } catch (err) {
        set({ isSubmitting: false, answerError: getApiErrorMessage(err, "Could not submit. Your answers are saved, so try again.") });
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

    loadProgress: async () => {
      set({ progressStatus: "loading", progressError: null });
      try {
        const [progress, recommendations] = await Promise.all([svc.getProgress(), svc.getRecommendations()]);
        set({ progress, recommendations, progressStatus: "ready" });
      } catch (err) {
        set({ progressStatus: "error", progressError: getApiErrorMessage(err, "Unable to load your Python progress.") });
      }
    },

    clearAnswerError: () => set({ answerError: null }),

    reset: () => {
      spent.clear();
      viewing = null;
      set({ ...EMPTY });
    },
  };
});
