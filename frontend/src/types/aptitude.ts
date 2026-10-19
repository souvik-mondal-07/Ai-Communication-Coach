/** Mirrors `app.schemas.aptitude` (Phase 23). Questions never carry an answer key until a session is submitted. */

export type AptitudeDifficulty = "easy" | "medium" | "hard";
export type AptitudeMode = "topic" | "scenario" | "timed_mock" | "mixed" | "weak";
export type AptitudeQuestionType = "direct" | "scenario" | "multi_step" | "data_interpretation" | "time_pressure";
export type CoverageStatus = "implemented" | "partial" | "missing";

export type DataSet =
  | { kind: "table"; title: string; columns: string[]; rows: (string | number)[][] }
  | { kind: "bar" | "line"; title: string; x_label: string; y_label: string; categories: string[]; series: { name: string; values: number[] }[] }
  | { kind: "pie"; title: string; unit: string; slices: { label: string; value: number }[] };

export interface SyllabusSubtopic {
  id: string;
  title: string;
  question_count: number;
  by_difficulty: Record<AptitudeDifficulty, number>;
  status: CoverageStatus;
}

export interface SyllabusTopic {
  id: string;
  code: string;
  title: string;
  section: string;
  summary: string;
  question_count: number;
  subtopics: SyllabusSubtopic[];
  items: { text: string; subtopic_ids: string[] }[];
  subtopics_implemented: number;
  subtopics_total: number;
  status: CoverageStatus;
}

export interface Syllabus {
  topics: SyllabusTopic[];
  totals: { topics: number; subtopics: number; subtopics_implemented: number; questions: number; min_questions_per_subtopic: number };
}

export interface AnswerFeedback {
  is_correct: boolean;
  correct_index: number;
  explanation: string;
  formula: string | null;
}

export interface SessionQuestion {
  question_id: string;
  topic_id: string;
  subtopic_id: string;
  question_type: AptitudeQuestionType;
  difficulty: AptitudeDifficulty;
  statement: string;
  options: string[];
  est_time_seconds: number;
  data: DataSet | null;
  selected_index: number | null;
  marked_for_review: boolean;
  locked: boolean;
  feedback: AnswerFeedback | null;
}

export interface AptitudeSession {
  session_id: string;
  mode: AptitudeMode;
  status: "in_progress" | "completed";
  difficulty: AptitudeDifficulty | null;
  question_count: number;
  requested_count: number;
  topic_ids: string[];
  immediate_feedback: boolean;
  exam_mode: boolean;
  started_at: string;
  expires_at: string | null;
  server_time: string;
  remaining_seconds: number | null;
  timer_minutes: number | null;
  questions: SessionQuestion[];
  scoring_policy: string;
}

export interface SessionRequest {
  mode: AptitudeMode;
  topic_ids: string[];
  subtopic_ids: string[];
  difficulty?: AptitudeDifficulty;
  question_count: number;
  timer_minutes?: number;
  immediate_feedback?: boolean;
}

export interface AnswerPayload {
  selected_index: number | null;
  marked_for_review: boolean;
  time_spent_seconds: number;
}

export interface SavedAnswer {
  question_id: string;
  selected_index: number | null;
  marked_for_review: boolean;
  locked: boolean;
  feedback: AnswerFeedback | null;
  remaining_seconds: number | null;
}

export interface TopicPerformance {
  topic_id: string;
  topic_title: string;
  total: number;
  correct: number;
  incorrect: number;
  unanswered: number;
  accuracy: number;
}

export interface ResultQuestion {
  question_id: string;
  topic_id: string;
  subtopic_id: string;
  difficulty: AptitudeDifficulty;
  statement: string;
  options: string[];
  data: DataSet | null;
  selected_index: number | null;
  correct_index: number;
  outcome: "correct" | "incorrect" | "unanswered";
  explanation: string;
  formula: string | null;
  marked_for_review: boolean;
  time_spent_seconds: number;
}

export interface AptitudeResult {
  session_id: string;
  mode: AptitudeMode;
  status: "completed";
  total_questions: number;
  correct: number;
  incorrect: number;
  unanswered: number;
  score: number;
  accuracy: number;
  time_taken_seconds: number;
  average_seconds_per_question: number;
  auto_submitted: boolean;
  started_at: string;
  finished_at: string | null;
  topic_performance: TopicPerformance[];
  revision_topics: { topic_id: string; topic_title: string; accuracy: number; subtopics: { subtopic_id: string; title: string }[] }[];
  questions: ResultQuestion[];
  scoring_policy: string;
}

export interface WeakTopic {
  topic_id: string;
  topic_title: string;
  answered: number;
  correct: number;
  accuracy: number;
  reason: string;
  weak_subtopics: { subtopic_id: string; title: string; accuracy: number; answered: number }[];
}

export interface Recommendations {
  has_history: boolean;
  weak_topics: WeakTopic[];
  incorrect_question_count: number;
  message: string;
  thresholds: { min_answered: number; accuracy_below: number };
}

export interface AptitudeProgress {
  sessions_completed: number;
  questions_presented: number;
  questions_answered: number;
  correct: number;
  incorrect: number;
  unanswered: number;
  accuracy: number;
  average_seconds_per_question: number | null;
  topic_accuracy: { topic_id: string; topic_title: string; answered: number; correct: number; presented: number; accuracy: number }[];
  difficulty_accuracy: { difficulty: AptitudeDifficulty; answered: number; correct: number; accuracy: number }[];
  recent_sessions: { session_id: string; mode: AptitudeMode; score: number; total: number; accuracy: number; time_taken_seconds: number; finished_at: string }[];
  trend: { session_id: string; accuracy: number; finished_at: string }[];
  improvement_points: number | null;
  weak_topics: WeakTopic[];
}
