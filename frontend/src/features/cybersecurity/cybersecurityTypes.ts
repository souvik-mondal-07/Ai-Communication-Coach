export type Difficulty = "beginner" | "intermediate" | "advanced";
export type QuestionType = "multiple_choice" | "short_answer";

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

export interface AnswerResult {
  score: number;
  correct: boolean;
  feedback: string;
  ideal_answer: string | null;
  missing_points: string[];
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

export const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};
