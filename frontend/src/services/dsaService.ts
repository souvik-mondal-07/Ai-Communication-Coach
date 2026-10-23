import { api } from "@/services/api";
import type { AnswerPayload, DsaProgress, DsaResult, DsaSession, Recommendations, SavedAnswer, SelfVerdict, SessionRequest, Syllabus } from "@/types/dsa";

/**
 * Client for /dsa. The user is identified by the bearer token only; nothing here sends a user id, score or answer key.
 * There is intentionally no "run code" call: the server never executes submitted code.
 */
interface Envelope<T> {
  success: boolean;
  message: string;
  data: T;
}

const unwrap = <T>(res: { data: Envelope<T> }): T => res.data.data;

export const getSyllabus = (signal?: AbortSignal) => api.get<Envelope<Syllabus>>("/dsa/syllabus", { signal }).then(unwrap);
export const createSession = (body: SessionRequest) => api.post<Envelope<DsaSession>>("/dsa/sessions", body).then(unwrap);
export const getSession = (id: string, signal?: AbortSignal) => api.get<Envelope<DsaSession>>(`/dsa/sessions/${id}`, { signal }).then(unwrap);
export const saveAnswer = (id: string, questionId: string, body: AnswerPayload) =>
  api.put<Envelope<SavedAnswer>>(`/dsa/sessions/${id}/answers/${questionId}`, body).then(unwrap);
export const submitSession = (id: string) => api.post<Envelope<DsaResult>>(`/dsa/sessions/${id}/submit`).then(unwrap);
export const getResult = (id: string, signal?: AbortSignal) => api.get<Envelope<DsaResult>>(`/dsa/sessions/${id}/result`, { signal }).then(unwrap);
export const setSelfAssessment = (id: string, questionId: string, verdict: SelfVerdict) =>
  api.put<Envelope<{ question_id: string; self_assessment: SelfVerdict; counts_toward_score: boolean }>>(`/dsa/sessions/${id}/self-assessment/${questionId}`, { verdict }).then(unwrap);
export const getProgress = (signal?: AbortSignal) => api.get<Envelope<DsaProgress>>("/dsa/progress", { signal }).then(unwrap);
export const getRecommendations = (signal?: AbortSignal) => api.get<Envelope<Recommendations>>("/dsa/recommendations", { signal }).then(unwrap);
