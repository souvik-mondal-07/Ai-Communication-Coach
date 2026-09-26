/**
 * Types for Pressure & Nervousness Training (Step 10). Mirror the backend's
 * public session view (`pressure_service._public_session`).
 *
 * This is a training system, not a diagnostic one: nothing here is a
 * nervousness/anxiety score. `pressure_indicators` are the same approximate
 * communication indicators used elsewhere (see `voiceTypes.ts`) — speaking
 * rate, filler words, pauses — never a psychological assessment.
 */
import type { InputMode, VoiceAnalysis } from "@/features/voice/voiceTypes";
import type { InterviewDifficulty, InterviewType } from "@/types/interview";

export const PRESSURE_LEVELS = [1, 2, 3, 4, 5] as const;
export type PressureLevel = (typeof PRESSURE_LEVELS)[number];

export type PressureMode = "interview" | "communication";
export type PressureStatus = "in_progress" | "completed" | "abandoned";
export type SelfReportedDifficulty = "easy" | "manageable" | "challenging" | "very_difficult";
export type PressureConditionType =
  | "none"
  | "time_pressure"
  | "topic_switch"
  | "difficult_question"
  | "ambiguous_question";
export type FollowUpKind = "rapid" | "interruption" | "technical";

export const SELF_REPORT_OPTIONS: { value: SelfReportedDifficulty; label: string }[] = [
  { value: "easy", label: "Easy" },
  { value: "manageable", label: "Manageable" },
  { value: "challenging", label: "Challenging" },
  { value: "very_difficult", label: "Very Difficult" },
];

export const CONDITION_LABELS: Record<PressureConditionType, string> = {
  none: "No added pressure",
  time_pressure: "Time pressure",
  topic_switch: "Topic switch",
  difficult_question: "Harder question",
  ambiguous_question: "Open-ended scenario",
};

export interface PressureLevelInfo {
  pressure_level: PressureLevel;
  label: string;
  description: string;
  characteristics: string[];
  time_limit_seconds: number | null;
  allow_hints: boolean;
}

export interface PressureConfig {
  pressureLevel: PressureLevel;
  mode: PressureMode;
  interviewType: InterviewType;
  difficulty: InterviewDifficulty;
  questionCount: number;
  inputMode: InputMode;
}

export interface PressureCondition {
  type: PressureConditionType;
  time_limit_seconds: number | null;
  topic_switched: boolean;
  difficulty_bumped: boolean;
}

/** Deterministic, observable indicators for one answer — text or voice. Never a diagnosis. */
export type PressureIndicators = VoiceAnalysis;

export interface PressureAnswerRecord {
  answer: string | null;
  answer_input_type: InputMode;
  response_duration_seconds: number | null;
  timed_out: boolean;
  pressure_indicators: PressureIndicators | null;
  technical_evaluation: import("@/types/interview").TechnicalEvaluation | null;
  communication_evaluation: import("@/types/interview").CommunicationEvaluation | null;
  improved_answer: string | null;
}

export interface PressureFollowUp extends PressureAnswerRecord {
  question: string;
  kind: FollowUpKind;
}

export interface PressureQuestion extends PressureAnswerRecord {
  question_number: number;
  question: string;
  topic: string;
  topic_label: string;
  condition: PressureCondition;
  technical_score: number | null;
  communication_score: number | null;
  follow_up_questions: PressureFollowUp[];
}

export interface CurrentPressurePrompt {
  question_number: number;
  question: string;
  topic: string;
  topic_label: string;
  is_follow_up: boolean;
  follow_up_kind: FollowUpKind | null;
  time_limit_seconds: number | null;
}

export interface PressureComparison {
  baseline_available: boolean;
  message?: string;
  normal_practice?: {
    technical_score: number | null;
    communication_score: number | null;
    speaking_rate_wpm: number | null;
    filler_words: number | null;
  };
}

export interface PressureFinalEvaluation {
  overall_score: number;
  technical_score: number;
  communication_score: number;
  pressure_handling_score: number | null;
  pressure_handling_label: string;
  response_control_score: number | null;
  clarity_score: number | null;
  strengths: string[];
  areas_to_improve: string[];
  pressure_indicators: string[];
  recommendations: string[];
  summary: string;
  ai_narrative_available: boolean;
  comparison: PressureComparison;
  voice_summary?: import("@/features/voice/voiceTypes").VoiceSummary;
}

export interface PressureSessionView {
  session_id: string;
  pressure_level: PressureLevel;
  mode: PressureMode;
  interview_type: InterviewType;
  difficulty: InterviewDifficulty;
  input_mode: InputMode;
  question_count: number;
  current_question_number: number;
  answered_count: number;
  status: PressureStatus;
  started_at: string;
  completed_at: string | null;
  current_prompt: CurrentPressurePrompt | null;
  questions: PressureQuestion[];
  self_reported_difficulty: SelfReportedDifficulty | null;
  self_report_note: string | null;
  final_evaluation: PressureFinalEvaluation | null;
}

export interface StartPressureResult {
  session_id: string;
  pressure_level: PressureLevel;
  question_number: number;
  question: string;
  topic_label: string;
  time_limit_seconds: number | null;
  status: PressureStatus;
  session: PressureSessionView;
}

export interface PressureResponseResult {
  pressure_indicators: PressureIndicators | null;
  next_prompt: string | null;
  next_prompt_kind: "question" | FollowUpKind | null;
  next_condition: PressureCondition | null;
  question_number: number;
  is_follow_up: boolean;
  session_complete: boolean;
  final_evaluation: PressureFinalEvaluation | null;
  session: PressureSessionView;
}

export interface PressureSummary {
  session_id: string;
  pressure_level: PressureLevel;
  mode: PressureMode;
  difficulty: InterviewDifficulty;
  question_count: number;
  answered_count: number;
  status: PressureStatus;
  overall_score: number | null;
  pressure_handling_score: number | null;
  self_reported_difficulty: SelfReportedDifficulty | null;
  started_at: string;
  completed_at: string | null;
}

export interface PressureHistoryPage {
  sessions: PressureSummary[];
  page: number;
  limit: number;
  total: number;
}
