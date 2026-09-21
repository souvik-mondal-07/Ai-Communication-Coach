/**
 * Types for the cybersecurity interview simulator (Step 9). These mirror the
 * backend's public interview session view (`interview_service._public_session`).
 *
 * While an interview is active (and "show feedback" is off) the backend sends
 * `null` for every evaluation, so all evaluation fields are nullable.
 */
import type { AudioMetadata, InputMode, VoiceAnalysis, VoiceSummary } from "@/features/voice/voiceTypes";

export type InterviewType = "hr" | "technical" | "cybersecurity" | "scenario_based" | "mixed";
export type InterviewDifficulty = "beginner" | "intermediate" | "advanced";
export type InterviewStatus = "in_progress" | "completed" | "abandoned";

/** Interview lengths offered by the setup screen (the API accepts exactly these). */
export const QUESTION_COUNTS = [5, 10, 15, 20] as const;

export const INTERVIEW_TYPE_OPTIONS: { value: InterviewType; label: string; description: string }[] = [
  { value: "hr", label: "HR", description: "Behavioural and personal questions" },
  { value: "technical", label: "Technical", description: "Core security knowledge" },
  { value: "cybersecurity", label: "Cybersecurity", description: "Full specialty spread" },
  { value: "scenario_based", label: "Scenario-Based", description: "Practical security situations" },
  { value: "mixed", label: "Mixed", description: "HR + technical + scenarios" },
];

export const INTERVIEW_TYPE_LABELS: Record<InterviewType, string> = {
  hr: "HR",
  technical: "Technical",
  cybersecurity: "Cybersecurity",
  scenario_based: "Scenario-Based",
  mixed: "Mixed",
};

export const INTERVIEW_DIFFICULTY_LABELS: Record<InterviewDifficulty, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

export interface InterviewConfig {
  interviewType: InterviewType;
  difficulty: InterviewDifficulty;
  questionCount: number;
  mode: InputMode;
  revealFeedback: boolean;
}

export interface TechnicalEvaluation {
  technical_score: number;
  accuracy: number;
  completeness: number;
  relevance: number;
  depth: number;
  /** Only for scenario questions. */
  practical_reasoning: number | null;
  feedback: string;
}

export interface CommunicationEvaluation {
  communication_score: number;
  clarity: number;
  grammar: number;
  vocabulary: number;
  structure: number;
  conciseness: number;
  professionalism: number;
  relevance: number;
  feedback: string;
}

/** One answered (or pending) prompt: a main question or a follow-up. */
export interface AnswerRecord {
  answer: string | null;
  answer_input_type: "text" | "voice";
  voice_analysis: VoiceAnalysis | null;
  technical_evaluation: TechnicalEvaluation | null;
  communication_evaluation: CommunicationEvaluation | null;
  improved_answer: string | null;
}

export interface FollowUpQuestion extends AnswerRecord {
  question: string;
}

export interface InterviewQuestion extends AnswerRecord {
  question_number: number;
  question: string;
  topic: string;
  topic_label: string;
  technical_score: number | null;
  communication_score: number | null;
  follow_up_questions: FollowUpQuestion[];
}

export interface CurrentPrompt {
  question_number: number;
  question: string;
  topic: string;
  topic_label: string;
  is_follow_up: boolean;
  follow_up_index: number | null;
}

export interface TopicScore {
  topic: string;
  label: string;
  average_score: number;
  questions: number;
}

export interface RecommendedPractice {
  title: string;
  /** Slug of an existing Cybersecurity Learning topic, when one matches. */
  slug: string | null;
}

export interface FinalEvaluation {
  overall_score: number;
  technical_score: number;
  communication_score: number;
  strengths: string[];
  weaknesses: string[];
  technical_weaknesses: string[];
  communication_weaknesses: string[];
  recommended_topics: string[];
  recommendations: string[];
  recommended_practice: RecommendedPractice[];
  weak_topics: TopicScore[];
  topic_scores: TopicScore[];
  answered_questions: number;
  summary: string;
  /** false when the written summary couldn't be generated (scores are still complete). */
  ai_narrative_available: boolean;
  voice_summary?: VoiceSummary;
}

export interface InterviewSessionView {
  session_id: string;
  interview_type: InterviewType;
  difficulty: InterviewDifficulty;
  mode: InputMode;
  question_count: number;
  current_question_number: number;
  answered_count: number;
  status: InterviewStatus;
  reveal_feedback: boolean;
  started_at: string;
  completed_at: string | null;
  current_prompt: CurrentPrompt | null;
  questions: InterviewQuestion[];
  final_evaluation: FinalEvaluation | null;
}

export interface StartInterviewResult {
  session_id: string;
  question_number: number;
  question: string;
}

/** Concise live feedback; only present when the interview was started with feedback on. */
export interface LiveEvaluation {
  technical_score: number;
  communication_score: number;
  feedback: string;
  communication_feedback: string;
}

export interface AnswerResult {
  evaluation: LiveEvaluation | null;
  next_question: string | null;
  question_number: number;
  is_follow_up: boolean;
  interview_complete: boolean;
  final_evaluation: FinalEvaluation | null;
  session: InterviewSessionView;
}

export interface InterviewSummary {
  session_id: string;
  interview_type: InterviewType;
  difficulty: InterviewDifficulty;
  mode: InputMode;
  question_count: number;
  answered_count: number;
  status: InterviewStatus;
  overall_score: number | null;
  technical_score: number | null;
  communication_score: number | null;
  started_at: string;
  completed_at: string | null;
}

export interface InterviewHistoryPage {
  sessions: InterviewSummary[];
  page: number;
  limit: number;
  total: number;
}

export type { AudioMetadata };
