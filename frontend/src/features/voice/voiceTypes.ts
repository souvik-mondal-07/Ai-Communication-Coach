/**
 * Types for the voice feature (Step 8). These mirror the backend's
 * `app/schemas/voice.py` and the `voice_analysis` / `voice_summary` objects
 * stored on communication sessions.
 *
 * All speaking metrics are approximate communication indicators — they are
 * not a psychological or medical assessment.
 */

export type InputMode = "text" | "voice";

export interface PauseMetrics {
  pause_count: number;
  long_pauses: number;
  average_pause_seconds: number | null;
  longest_pause_seconds: number | null;
  total_pause_seconds: number;
  granularity: "word" | "segment";
}

export interface TranscribeResult {
  text: string;
  language: string | null;
  duration_seconds: number;
  /** null when the recording had too little timing information to measure. */
  pause_metrics: PauseMetrics | null;
}

/** Audio metadata sent back with a transcript the user chooses to submit. */
export interface AudioMetadata {
  duration_seconds: number;
  language?: string | null;
  pause_metrics?: PauseMetrics | null;
}

export interface SendMessageOptions {
  inputType?: InputMode;
  audioMetadata?: AudioMetadata;
  transcriptEdited?: boolean;
}

export interface VoiceCapabilities {
  stt_available: boolean;
  tts_available: boolean;
  max_audio_seconds: number;
  max_audio_bytes: number;
}

/** Per-message speaking metrics. `null` means "not measurable", never zero. */
export interface VoiceAnalysis {
  word_count: number;
  sentence_count: number;
  average_sentence_length: number;
  duration_seconds: number | null;
  speaking_rate_wpm: number | null;
  speaking_rate_label: "slow" | "moderate" | "fast" | null;
  filler_words: Record<string, number>;
  total_filler_words: number;
  repeated_words: Record<string, number>;
  pause_count: number | null;
  long_pauses: number | null;
  average_pause_seconds: number | null;
  longest_pause_seconds: number | null;
  transcript_edited: boolean;
}

export interface VoiceSummary {
  voice_message_count: number;
  total_words_spoken: number;
  total_speaking_duration_seconds: number | null;
  average_speaking_rate_wpm: number | null;
  speaking_rate_label: "slow" | "moderate" | "fast" | null;
  total_filler_words: number;
  filler_words: Record<string, number>;
  pause_count: number | null;
  long_pauses: number | null;
  average_pause_seconds: number | null;
  longest_pause_seconds: number | null;
  clarity_score: number | null;
  grammar_score: number | null;
  vocabulary_score: number | null;
  conciseness_score: number | null;
  strengths: string[];
  improvements: string[];
  summary: string | null;
  ai_feedback_available: boolean;
}
