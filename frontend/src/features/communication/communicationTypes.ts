import type { VoiceAnalysis, VoiceSummary } from "@/features/voice/voiceTypes";

export type Category =
  | "classmates"
  | "teachers"
  | "seniors"
  | "recruiters"
  | "teammates"
  | "managers"
  | "everyday"
  | "professional";

export type Mode = "daily_life" | "professional" | "social" | "difficult_conversation" | "roleplay";
export type Difficulty = "beginner" | "intermediate" | "advanced";
export type SessionStatus = "in_progress" | "completed";

export interface ScenarioSummary {
  scenario_id: string;
  title: string;
  slug: string;
  category: Category;
  mode: Mode;
  difficulty: Difficulty;
  description: string;
  objective: string;
  skills_targeted: string[];
}

export interface ScenarioDetail extends ScenarioSummary {
  context: string;
  ai_role: string;
  user_role: string;
  opening_message: string;
  tips: string[];
}

export interface CommunicationMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  /** Absent on messages from before voice mode existed (treat as "text"). */
  input_type?: "text" | "voice";
  voice_analysis?: VoiceAnalysis | null;
}

export interface BetterResponse {
  original: string;
  improved: string;
  why: string;
}

export interface Evaluation {
  overall_score: number;
  clarity_score: number;
  grammar_score: number;
  vocabulary_score: number;
  professionalism_score: number;
  confidence_score: number;
  relevance_score: number;
  conversation_flow_score: number;
  strengths: string[];
  weaknesses: string[];
  improvements: string[];
  better_responses: BetterResponse[];
  summary: string;
  /** Present only when the session included spoken messages. */
  voice_summary?: VoiceSummary;
}

export interface SessionSummary {
  session_id: string;
  scenario_title: string;
  category: Category;
  mode: Mode;
  difficulty: Difficulty;
  status: SessionStatus;
  overall_score: number | null;
  started_at: string;
  completed_at: string | null;
}

export interface SessionDetail extends SessionSummary {
  ai_role: string;
  user_role: string;
  objective: string;
  messages: CommunicationMessage[];
  evaluation: Evaluation | null;
}

export const CATEGORY_LABELS: Record<Category, string> = {
  classmates: "Classmates",
  teachers: "Teachers / Professors",
  seniors: "Seniors",
  recruiters: "Recruiters",
  teammates: "Teammates",
  managers: "Managers / Team Leads",
  everyday: "Everyday Social",
  professional: "Professional",
};

export const MODE_LABELS: Record<Mode, string> = {
  daily_life: "Daily Life",
  professional: "Professional",
  social: "Social",
  difficult_conversation: "Difficult Conversation",
  roleplay: "Roleplay",
};

export const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

export const SCORE_FIELDS: { key: keyof Evaluation; label: string }[] = [
  { key: "clarity_score", label: "Clarity" },
  { key: "grammar_score", label: "Grammar" },
  { key: "vocabulary_score", label: "Vocabulary" },
  { key: "professionalism_score", label: "Professionalism" },
  { key: "confidence_score", label: "Confidence" },
  { key: "relevance_score", label: "Relevance" },
  { key: "conversation_flow_score", label: "Conversation Flow" },
];
