import { api } from "@/services/api";
import type {
  AnswerPayload, AptitudeProgress, AptitudeResult, AptitudeSession, Recommendations, SavedAnswer, SessionRequest, Syllabus,
} from "@/types/aptitude";

/** Client for /aptitude. The user is identified by the bearer token only; nothing here sends a user id, score or answer key. */
interface Envelope<T> {
  success: boolean;
  message: string;
  data: T;
}

const unwrap = <T>(res: { data: Envelope<T> }): T => res.data.data;

export const getSyllabus = (signal?: AbortSignal) => api.get<Envelope<Syllabus>>("/aptitude/syllabus", { signal }).then(unwrap);
export const createSession = (body: SessionRequest) => api.post<Envelope<AptitudeSession>>("/aptitude/sessions", body).then(unwrap);
export const getSession = (id: string, signal?: AbortSignal) => api.get<Envelope<AptitudeSession>>(`/aptitude/sessions/${id}`, { signal }).then(unwrap);
export const saveAnswer = (id: string, questionId: string, body: AnswerPayload) =>
  api.put<Envelope<SavedAnswer>>(`/aptitude/sessions/${id}/answers/${questionId}`, body).then(unwrap);
export const submitSession = (id: string) => api.post<Envelope<AptitudeResult>>(`/aptitude/sessions/${id}/submit`).then(unwrap);
export const getResult = (id: string, signal?: AbortSignal) => api.get<Envelope<AptitudeResult>>(`/aptitude/sessions/${id}/result`, { signal }).then(unwrap);
export const getProgress = (signal?: AbortSignal) => api.get<Envelope<AptitudeProgress>>("/aptitude/progress", { signal }).then(unwrap);
export const getRecommendations = (signal?: AbortSignal) => api.get<Envelope<Recommendations>>("/aptitude/recommendations", { signal }).then(unwrap);
