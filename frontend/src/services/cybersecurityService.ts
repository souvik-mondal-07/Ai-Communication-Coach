import { api } from "@/services/api";
import type {
  AnswerResult,
  Difficulty,
  PracticeCompleteResult,
  PracticeHistoryResult,
  PracticeStartResult,
  ProgressResult,
  TopicDetail,
  TopicSummary,
} from "@/features/cybersecurity/cybersecurityTypes";

/**
 * Client for the cybersecurity learning/practice endpoints. Talks only to
 * FastAPI (`/api/v1/cybersecurity/...`) — question generation and answer
 * evaluation happen server-side via Gemini; this file never calls an AI
 * provider directly.
 */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export async function getTopics(filters?: {
  category?: string;
  difficulty?: Difficulty;
}): Promise<TopicSummary[]> {
  const { data } = await api.get<ApiEnvelope<{ topics: TopicSummary[] }>>(
    "/cybersecurity/topics",
    { params: filters }
  );
  return data.data.topics;
}

export async function getTopic(slug: string): Promise<TopicDetail> {
  const { data } = await api.get<ApiEnvelope<{ topic: TopicDetail }>>(
    `/cybersecurity/topics/${encodeURIComponent(slug)}`
  );
  return data.data.topic;
}

export async function startPractice(params: {
  topicSlug: string;
  difficulty?: Difficulty;
  questionCount?: number;
}): Promise<PracticeStartResult> {
  const { data } = await api.post<ApiEnvelope<PracticeStartResult>>(
    "/cybersecurity/practice/start",
    {
      topic_slug: params.topicSlug,
      difficulty: params.difficulty,
      question_count: params.questionCount,
    }
  );
  return data.data;
}

export async function submitAnswer(params: {
  sessionId: string;
  questionId: string;
  answer: string;
}): Promise<AnswerResult> {
  const { data } = await api.post<ApiEnvelope<AnswerResult>>(
    `/cybersecurity/practice/${encodeURIComponent(params.sessionId)}/answer`,
    { question_id: params.questionId, answer: params.answer }
  );
  return data.data;
}

export async function completePractice(sessionId: string): Promise<PracticeCompleteResult> {
  const { data } = await api.post<ApiEnvelope<PracticeCompleteResult>>(
    `/cybersecurity/practice/${encodeURIComponent(sessionId)}/complete`
  );
  return data.data;
}

export async function getPracticeHistory(params?: {
  page?: number;
  limit?: number;
}): Promise<PracticeHistoryResult> {
  const { data } = await api.get<ApiEnvelope<PracticeHistoryResult>>(
    "/cybersecurity/practice/history",
    { params }
  );
  return data.data;
}

export async function getProgress(): Promise<ProgressResult> {
  const { data } = await api.get<ApiEnvelope<ProgressResult>>("/cybersecurity/progress");
  return data.data;
}
