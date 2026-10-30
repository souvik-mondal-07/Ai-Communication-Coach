import { api } from "@/services/api";
import type {
  AnswerPayload, CheckOutcome, Coverage, HintOutcome, HistoryPage, PyProgress, PyResult, PySession, Recommendations, RevealOutcome, RunOutcome, RunnerStatus, SavedAnswer, SessionRequest, Syllabus,
} from "@/types/pythonPractice";

/**
 * Client for /python-practice. The user is identified by the bearer token only; nothing here sends a user id, score, correctness flag, test result or answer key.
 * Source code is sent to the server, which runs it ONLY in its isolated runner (or refuses when no runner is available); this client never executes code.
 */
interface Envelope<T> {
  success: boolean;
  message: string;
  data: T;
}

const unwrap = <T>(res: { data: Envelope<T> }): T => res.data.data;
const base = "/python-practice";
const q = (id: string, qid: string) => `${base}/sessions/${id}/questions/${qid}`;

export const getRunner = (signal?: AbortSignal) => api.get<Envelope<RunnerStatus>>(`${base}/runner`, { signal }).then(unwrap);
export const getSyllabus = (signal?: AbortSignal) => api.get<Envelope<Syllabus>>(`${base}/syllabus`, { signal }).then(unwrap);
export const getCoverage = (signal?: AbortSignal) => api.get<Envelope<Coverage>>(`${base}/coverage`, { signal }).then(unwrap);
export const createSession = (body: SessionRequest) => api.post<Envelope<PySession>>(`${base}/sessions`, body).then(unwrap);
export const getSession = (id: string, signal?: AbortSignal) => api.get<Envelope<PySession>>(`${base}/sessions/${id}`, { signal }).then(unwrap);
export const getHistory = (page = 1, limit = 10, signal?: AbortSignal) => api.get<Envelope<HistoryPage>>(`${base}/sessions`, { params: { page, limit }, signal }).then(unwrap);
export const saveAnswer = (id: string, qid: string, body: AnswerPayload) => api.put<Envelope<SavedAnswer>>(`${base}/sessions/${id}/answers/${qid}`, body).then(unwrap);
export const runCode = (id: string, qid: string, code: string) => api.post<Envelope<RunOutcome>>(`${q(id, qid)}/run`, { code }).then(unwrap);
export const checkAnswer = (id: string, qid: string, body: { code?: string; text?: string; time_spent_seconds: number }) => api.post<Envelope<CheckOutcome>>(`${q(id, qid)}/check`, body).then(unwrap);
export const revealSolution = (id: string, qid: string) => api.post<Envelope<RevealOutcome>>(`${q(id, qid)}/reveal`).then(unwrap);
export const requestHint = (id: string, qid: string) => api.post<Envelope<HintOutcome>>(`${q(id, qid)}/hint`).then(unwrap);
export const submitSession = (id: string) => api.post<Envelope<PyResult>>(`${base}/sessions/${id}/submit`).then(unwrap);
export const getResult = (id: string, signal?: AbortSignal) => api.get<Envelope<PyResult>>(`${base}/sessions/${id}/result`, { signal }).then(unwrap);
export const getProgress = (signal?: AbortSignal) => api.get<Envelope<PyProgress>>(`${base}/progress`, { signal }).then(unwrap);
export const getRecommendations = (signal?: AbortSignal) => api.get<Envelope<Recommendations>>(`${base}/recommendations`, { signal }).then(unwrap);
