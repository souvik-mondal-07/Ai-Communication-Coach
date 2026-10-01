export type VoiceConversationMode =
  | "general"
  | "cybersecurity"
  | "practice"
  | "communication"
  | "interview"
  | "pressure";

export type VoiceConversationStatus = "created" | "active" | "completed" | "abandoned";
export type VoiceDifficulty = "beginner" | "intermediate" | "advanced";
export type VoiceInterviewType = "hr" | "technical" | "cybersecurity" | "scenario_based" | "mixed";

export const VOICE_MODE_LABELS: Record<VoiceConversationMode, string> = {
  general: "General conversation",
  cybersecurity: "Cybersecurity Q&A",
  practice: "Topic practice",
  communication: "Communication practice",
  interview: "Interview",
  pressure: "Pressure training",
};

export const VOICE_MODE_DESCRIPTIONS: Record<VoiceConversationMode, string> = {
  general: "Talk with your mentor about anything in your learning or career.",
  cybersecurity: "The mentor asks cybersecurity questions and discusses your answers.",
  practice: "Focused spoken practice on one topic you choose.",
  communication: "Role-play a real-life conversation and get communication feedback.",
  interview: "A spoken interview with follow-up questions and a final evaluation.",
  pressure: "An interview under interruptions and time pressure.",
};

export const VOICE_DIFFICULTY_LABELS: Record<VoiceDifficulty, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

export interface VoiceAnalysis {
  word_count: number | null;
  duration_seconds: number | null;
  speaking_rate_wpm: number | null;
  total_filler_words: number | null;
  sentence_count: number | null;
  average_sentence_length: number | null;
  [key: string]: unknown;
}

export interface VoiceConversationTurn {
  role: "assistant" | "user";
  text: string;
  timestamp: string | null;
  audio_available?: boolean;
  duration_seconds?: number | null;
  voice_analysis?: VoiceAnalysis | null;
}

export interface LinkedSession {
  kind: "interview" | "pressure" | "communication";
  session_id: string;
  label?: string | null;
}

export interface VoiceConversationSession {
  session_id: string;
  mode: VoiceConversationMode;
  mode_label: string;
  difficulty: VoiceDifficulty;
  topic: string | null;
  status: VoiceConversationStatus;
  started_at: string | null;
  last_activity_at: string | null;
  ended_at: string | null;
  turn_count: number;
  user_turn_count: number;
  assistant_turn_count: number;
  max_session_turns: number;
  linked_session: LinkedSession | null;
  messages: VoiceConversationTurn[];
  summary: VoiceConversationSummary | null;
}

export type VoiceConversationSessionRow = Omit<
  VoiceConversationSession,
  "messages" | "summary" | "linked_session" | "last_activity_at" | "assistant_turn_count" | "max_session_turns"
>;

export interface VoiceConversationSummary {
  mode: VoiceConversationMode;
  mode_label: string;
  difficulty: VoiceDifficulty;
  topic: string | null;
  turns: number;
  duration_seconds: number;
  average_response_duration_seconds: number | null;
  average_response_words: number | null;
  /** Aggregate of the measured answers (Step 8); null when none were analysed. */
  speaking_metrics: Record<string, unknown> | null;
  evaluation: Record<string, unknown> | null;
  evaluation_available: boolean;
  evaluation_error: boolean;
  strengths: string[];
  areas_to_improve: string[];
}

/** Returned by both `/start` and `/respond` turns. */
export interface VoiceConversationResponse {
  user_transcript?: string;
  user_voice_analysis?: VoiceAnalysis | null;
  ai_response: string;
  audio_url: string | null;
  audio_error: "TTS_NOT_CONFIGURED" | "TTS_FAILED" | null;
  turn_number: number;
  conversation_complete: boolean;
  summary?: VoiceConversationSummary | null;
  mode_info: Record<string, unknown>;
}

export interface VoiceConversationStartResponse extends VoiceConversationResponse {
  session: VoiceConversationSession;
  resumed: boolean;
}

/** Pause statistics measured during transcription; echoed back unchanged with the transcript. */
export interface PauseMetrics {
  pause_count: number;
  long_pauses: number;
  average_pause_seconds: number | null;
  longest_pause_seconds: number | null;
  total_pause_seconds: number;
  granularity: "word" | "segment";
}

/** What was measured from the audio while transcribing. Needs no audio to be reused. */
export interface TranscriptionMeta {
  duration_seconds: number | null;
  language: string | null;
  pause_metrics: PauseMetrics | null;
}

/** Result of `POST …/transcribe`: speech-to-text only. No AI, no speech, nothing saved. */
export interface TranscriptionResult extends TranscriptionMeta {
  transcript: string;
  /** True when nothing usable was heard; `transcript` is then "". */
  is_empty: boolean;
}

/**
 * An answer that was transcribed successfully but whose AI reply failed. It holds
 * everything "Retry response" needs -- the transcript and its metadata -- and
 * deliberately no audio: retrying never re-sends a recording or re-runs STT.
 */
export interface FailedResponse {
  transcript: string;
  /** Answers already given when this answer was made; the server rejects stale/duplicate submissions. */
  expectedTurn: number;
  responseSeconds?: number;
  meta: TranscriptionMeta;
}

/** Which step of an answer the server is working on. */
export type AnswerPhase = "transcribing" | "processing";

/** Exactly what the learner sees when speech-to-text produced nothing usable. */
export const EMPTY_TRANSCRIPT_MESSAGE = "I couldn't hear a clear response. Please try again.";

/** null, undefined, "", and whitespace-only text (spaces, newlines, tabs) are never valid transcripts. */
export function isBlankTranscript(value: string | null | undefined): boolean {
  return typeof value !== "string" || value.trim().length === 0;
}

export interface VoiceConversationConfig {
  stt_available: boolean;
  tts_available: boolean;
  max_recording_seconds: number;
  max_audio_bytes: number;
  max_session_turns: number;
  auto_play: boolean;
  modes: VoiceConversationMode[];
}

export interface CreateVoiceConversationInput {
  mode: VoiceConversationMode;
  difficulty: VoiceDifficulty;
  topic?: string;
  interview_type?: VoiceInterviewType;
  question_count?: number;
  pressure_level?: number;
}

/**
 * What the page is doing right now. Drives the status line and the controls.
 * An answer moves: ready → listening → transcribing → processing → ai_speaking → ready.
 */
export type VoiceUiState =
  | "idle"
  | "starting"
  | "ai_speaking"
  | "ready"
  | "listening"
  | "transcribing"
  | "processing"
  | "paused"
  | "error"
  | "completed";

export type MicPermission = "unknown" | "granted" | "denied" | "unavailable";
