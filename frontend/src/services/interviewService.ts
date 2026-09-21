import { api } from "@/services/api";
import type { SendMessageOptions } from "@/features/voice/voiceTypes";
import type {
  AnswerResult,
  InterviewConfig,
  InterviewHistoryPage,
  InterviewSessionView,
  StartInterviewResult,
} from "@/types/interview";

/**
 * Client for `/api/v1/interview/...`. Only FastAPI is called — the interviewer
 * AI, evaluation and (for voice) transcription all run on the backend.
 */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export async function startInterview(config: InterviewConfig): Promise<StartInterviewResult> {
  const { data } = await api.post<ApiEnvelope<StartInterviewResult>>("/interview/sessions", {
    interview_type: config.interviewType,
    difficulty: config.difficulty,
    question_count: config.questionCount,
    mode: config.mode,
    reveal_feedback: config.revealFeedback,
  });
  return data.data;
}

export async function getInterview(sessionId: string): Promise<InterviewSessionView> {
  const { data } = await api.get<ApiEnvelope<InterviewSessionView>>(
    `/interview/sessions/${encodeURIComponent(sessionId)}`
  );
  return data.data;
}

export async function listInterviews(page = 1, limit = 10): Promise<InterviewHistoryPage> {
  const { data } = await api.get<ApiEnvelope<InterviewHistoryPage>>("/interview/sessions", {
    params: { page, limit },
  });
  return data.data;
}

/** Submit an answer. Voice answers reuse the Step 8 transcript + audio metadata. */
export async function submitAnswer(
  sessionId: string,
  answer: string,
  options?: SendMessageOptions
): Promise<AnswerResult> {
  // Text answers send the minimal body; voice adds the Step 8 fields.
  const body =
    options?.inputType === "voice"
      ? {
          answer,
          input_type: "voice",
          audio_metadata: options.audioMetadata,
          transcript_edited: options.transcriptEdited ?? false,
        }
      : { answer };
  const { data } = await api.post<ApiEnvelope<AnswerResult>>(
    `/interview/sessions/${encodeURIComponent(sessionId)}/answer`,
    body
  );
  return data.data;
}

export async function completeInterview(sessionId: string): Promise<InterviewSessionView> {
  const { data } = await api.post<ApiEnvelope<{ session: InterviewSessionView }>>(
    `/interview/sessions/${encodeURIComponent(sessionId)}/complete`
  );
  return data.data.session;
}
