export type Difficulty = "beginner" | "intermediate" | "advanced";
export type QuestionType =
  | "multiple_choice"
  | "short_answer"
  | "scenario"
  | "troubleshooting"
  | "command";

export interface TopicSummary {
  slug: string;
  title: string;
  category: string;
  difficulty: Difficulty;
  description: string;
  practice_enabled: boolean;
}

export interface TopicDetail extends TopicSummary {
  learning_objectives: string[];
  content: string;
  examples: string[];
  key_points: string[];
}

export interface PublicQuestion {
  question_id: string;
  question: string;
  type: QuestionType;
  options: string[] | null;
}

export interface PracticeStartResult {
  session_id: string;
  topic_slug: string;
  topic_title: string;
  difficulty: Difficulty;
  questions: PublicQuestion[];
}

export interface DimensionScores {
  technical: number;
  completeness: number;
  reasoning: number;
  practicality: number;
  overall: number;
}

export interface AnswerResult {
  score: number;
  correct: boolean;
  feedback: string;
  ideal_answer: string | null;
  missing_points: string[];
  // Step 17 (absent/empty for Step 5 sessions)
  raw_score?: number | null;
  hints_used?: number;
  hint_penalty?: number;
  dimension_scores?: DimensionScores | null;
  strengths?: string[];
  improvement?: string | null;
  explanation?: string | null;
  ideal_steps?: string[] | null;
  revealed?: boolean;
}

export interface RecommendedNext {
  title: string;
  topic: string | null;
  topic_slug: string | null;
  difficulty: Difficulty | null;
  reasons: string[];
  basis: string | null;
  source: "personalization" | "session";
}

export interface PracticeCompleteResult {
  session_id: string;
  score: number;
  questions_answered: number;
  correct_answers: number;
  topic_title: string;
  category: string;
  weak_areas: string[];
  recommendations: string[];
  // Step 17 summary (absent for Step 5 sessions)
  mode?: string | null;
  scored?: boolean;
  questions_total?: number | null;
  needs_improvement?: number | null;
  hints_used?: number | null;
  categories?: string[];
  difficulty?: Difficulty | null;
  difficulty_mode?: "fixed" | "adaptive" | null;
  strong_areas?: string[];
  needs_work?: string[];
  recommended_next?: RecommendedNext | null;
  duration_seconds?: number | null;
  timed_out?: boolean;
  unanswered?: number | null;
}

export interface PracticeHistoryItem {
  session_id: string;
  topic_slug: string;
  topic_title: string;
  category: string;
  difficulty: Difficulty;
  status: "in_progress" | "completed";
  score: number | null;
  questions_answered: number;
  started_at: string;
  completed_at: string | null;
}

export interface PracticeHistoryResult {
  sessions: PracticeHistoryItem[];
  page: number;
  limit: number;
  total: number;
}

export interface ProgressCategory {
  category: string;
  average_score: number;
  attempts: number;
  status: "weak" | "developing" | "strong";
}

export interface ProgressResult {
  categories: ProgressCategory[];
  weak_categories: string[];
}

// --- Step 17: advanced practice ---------------------------------------------------

export type PracticeMode =
  | "personalized"
  | "topic"
  | "random"
  | "weakness"
  | "scenario"
  | "troubleshooting"
  | "interview";
export type PracticeDifficulty = Difficulty | "adaptive";
export type QuestionTypeChoice = "mixed" | QuestionType;

export interface PracticeModeInfo {
  id: PracticeMode;
  label: string;
  description: string;
  category: "none" | "optional" | "required";
  fixed_type: QuestionType | null;
}

export interface PracticeCategoryInfo {
  category: string;
  question_types: QuestionType[];
  topics: { slug: string; title: string; difficulty: Difficulty }[];
}

export interface PracticeConfig {
  modes: PracticeModeInfo[];
  difficulties: PracticeDifficulty[];
  question_types: QuestionTypeChoice[];
  categories: PracticeCategoryInfo[];
  limits: {
    min_questions: number;
    max_questions: number;
    default_questions: number;
    min_time_limit_minutes: number;
    max_time_limit_minutes: number;
    max_hints: number;
  };
}

export interface PracticeSessionConfig {
  mode: PracticeMode;
  category?: string | null;
  difficulty: PracticeDifficulty;
  questionType: QuestionTypeChoice;
  questionCount: number;
  timeLimitMinutes?: number | null;
}

export interface PracticeQuestionState {
  question_id: string;
  index: number;
  question: string;
  type: QuestionType;
  options: string[] | null;
  topic_title: string | null;
  category: string | null;
  difficulty: Difficulty | null;
  hints_available: number;
  hints_used: number;
  hints: string[];
  answered: boolean;
  result: AnswerResult | null;
}

export interface PracticeSessionState {
  session_id: string;
  mode: PracticeMode;
  status: "in_progress" | "completed";
  topic_slug: string | null;
  topic_title: string | null;
  category: string | null;
  categories: string[];
  difficulty: Difficulty | null;
  difficulty_mode: "fixed" | "adaptive";
  question_type: QuestionTypeChoice;
  question_count: number;
  started_at: string | null;
  time_limit_seconds: number | null;
  remaining_seconds: number | null;
  note: string | null;
  focus: { category: string; reason: string }[];
  questions: PracticeQuestionState[];
  has_more_questions: boolean;
  can_request_next: boolean;
  summary: PracticeCompleteResult | null;
}

export type HintResult =
  | {
      kind: "hint";
      hint_number: number;
      hint: string;
      hints_used: number;
      hints_remaining: number;
      max_score: number;
    }
  | { kind: "explanation"; hints_used: number; hints_remaining: number; result: AnswerResult };

export const MODE_LABELS: Record<PracticeMode, string> = {
  personalized: "Personalized",
  topic: "Topic",
  random: "Random",
  weakness: "My Weaknesses",
  scenario: "Scenario",
  troubleshooting: "Troubleshooting",
  interview: "Interview-style",
};

export const QUESTION_TYPE_LABELS: Record<QuestionTypeChoice, string> = {
  mixed: "Mixed",
  multiple_choice: "Multiple choice",
  short_answer: "Short answer",
  scenario: "Scenario",
  troubleshooting: "Troubleshooting",
  command: "Command / technical task",
};

export const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

export const PRACTICE_DIFFICULTY_LABELS: Record<PracticeDifficulty, string> = {
  ...DIFFICULTY_LABELS,
  adaptive: "Adaptive",
};
