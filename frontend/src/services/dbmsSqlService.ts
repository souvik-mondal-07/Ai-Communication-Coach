import { api } from "@/services/api";
import type {
  AnswerPayload, CheckOutcome, Dataset, DbmsProgress, DbmsResult, DbmsSession, HintOutcome, Recommendations, RevealOutcome, RunResult, SavedAnswer, SessionRequest, Syllabus,
} from "@/types/dbmsSql";

/**
 * Client for /dbms-sql. The user is identified by the bearer token only; nothing here sends a user id, score, correctness flag or answer key.
 * SQL text is sent to the server, which runs it ONLY in its isolated read-only sandbox; this client never executes SQL.
 */
interface Envelope<T> {
  success: boolean;
  message: string;
  data: T;
}

const unwrap = <T>(res: { data: Envelope<T> }): T => res.data.data;
const base = "/dbms-sql";

export const getSyllabus = (signal?: AbortSignal) => api.get<Envelope<Syllabus>>(`${base}/syllabus`, { signal }).then(unwrap);
export const getDataset = (id: string, signal?: AbortSignal) => api.get<Envelope<Dataset>>(`${base}/datasets/${id}`, { signal }).then(unwrap);
export const runSandbox = (sql: string, datasetId = "practice") => api.post<Envelope<RunResult>>(`${base}/sandbox/run`, { sql, dataset_id: datasetId }).then(unwrap);
export const createSession = (body: SessionRequest) => api.post<Envelope<DbmsSession>>(`${base}/sessions`, body).then(unwrap);
export const getSession = (id: string, signal?: AbortSignal) => api.get<Envelope<DbmsSession>>(`${base}/sessions/${id}`, { signal }).then(unwrap);
export const saveAnswer = (id: string, questionId: string, body: AnswerPayload) => api.put<Envelope<SavedAnswer>>(`${base}/sessions/${id}/answers/${questionId}`, body).then(unwrap);
export const checkAnswer = (id: string, questionId: string, body: { sql?: string; text?: string; time_spent_seconds: number }) =>
  api.post<Envelope<CheckOutcome>>(`${base}/sessions/${id}/questions/${questionId}/check`, body).then(unwrap);
export const revealSolution = (id: string, questionId: string) => api.post<Envelope<RevealOutcome>>(`${base}/sessions/${id}/questions/${questionId}/reveal`).then(unwrap);
export const requestHint = (id: string, questionId: string) => api.post<Envelope<HintOutcome>>(`${base}/sessions/${id}/questions/${questionId}/hint`).then(unwrap);
export const submitSession = (id: string) => api.post<Envelope<DbmsResult>>(`${base}/sessions/${id}/submit`).then(unwrap);
export const getResult = (id: string, signal?: AbortSignal) => api.get<Envelope<DbmsResult>>(`${base}/sessions/${id}/result`, { signal }).then(unwrap);
export const getProgress = (signal?: AbortSignal) => api.get<Envelope<DbmsProgress>>(`${base}/progress`, { signal }).then(unwrap);
export const getRecommendations = (signal?: AbortSignal) => api.get<Envelope<Recommendations>>(`${base}/recommendations`, { signal }).then(unwrap);
