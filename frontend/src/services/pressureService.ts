import { api } from "@/services/api";
import type { SendMessageOptions } from "@/features/voice/voiceTypes";
import type {
  PressureConfig,
  PressureHistoryPage,
  PressureLevelInfo,
  PressureResponseResult,
  PressureSessionView,
  SelfReportedDifficulty,
  StartPressureResult,
} from "@/types/pressure";

/**
 * Client for `/api/v1/pressure/...`. Only FastAPI is called — question
 * generation, evaluation and (for voice) transcription all reuse the
 * existing interview/voice backend services.
 */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export async function getPressureLevels(): Promise<PressureLevelInfo[]> {
  const { data } = await api.get<ApiEnvelope<{ levels: PressureLevelInfo[] }>>("/pressure/config");
  return data.data.levels;
}

export async function startPressureSession(config: PressureConfig): Promise<StartPressureResult> {
  const { data } = await api.post<ApiEnvelope<StartPressureResult>>("/pressure/sessions", {
    pressure_level: config.pressureLevel,
    mode: config.mode,
    interview_type: config.interviewType,
    difficulty: config.difficulty,
    question_count: config.questionCount,
    input_mode: config.inputMode,
  });
  return data.data;
}

export async function getPressureSession(sessionId: string): Promise<PressureSessionView> {
  const { data } = await api.get<ApiEnvelope<PressureSessionView>>(
    `/pressure/sessions/${encodeURIComponent(sessionId)}`
  );
  return data.data;
}

export async function listPressureSessions(page = 1, limit = 10): Promise<PressureHistoryPage> {
  const { data } = await api.get<ApiEnvelope<PressureHistoryPage>>("/pressure/sessions", {
    params: { page, limit },
  });
  return data.data;
}

interface SubmitOptions extends SendMessageOptions {
  /** True when the on-screen timer reached zero; a blank answer is then accepted, not discarded. */
  timedOut?: boolean;
  responseDurationSeconds?: number;
}

export async function submitPressureResponse(
  sessionId: string,
  answer: string,
  options?: SubmitOptions
): Promise<PressureResponseResult> {
  const body = {
    answer,
    input_type: options?.inputType ?? "text",
    ...(options?.inputType === "voice" && options.audioMetadata
      ? { audio_metadata: options.audioMetadata, transcript_edited: options.transcriptEdited ?? false }
      : {}),
    ...(options?.responseDurationSeconds !== undefined
      ? { response_duration_seconds: options.responseDurationSeconds }
      : {}),
    timed_out: options?.timedOut ?? false,
  };
  const { data } = await api.post<ApiEnvelope<PressureResponseResult>>(
    `/pressure/sessions/${encodeURIComponent(sessionId)}/response`,
    body
  );
  return data.data;
}

export async function completePressureSession(sessionId: string): Promise<PressureSessionView> {
  const { data } = await api.post<ApiEnvelope<{ session: PressureSessionView }>>(
    `/pressure/sessions/${encodeURIComponent(sessionId)}/complete`
  );
  return data.data.session;
}

export async function submitSelfReport(
  sessionId: string,
  difficulty: SelfReportedDifficulty,
  note?: string
): Promise<PressureSessionView> {
  const { data } = await api.post<ApiEnvelope<PressureSessionView>>(
    `/pressure/sessions/${encodeURIComponent(sessionId)}/self-report`,
    { difficulty, note }
  );
  return data.data;
}
