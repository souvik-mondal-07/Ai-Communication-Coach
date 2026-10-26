/** Mirrors `app.schemas.dbms_sql` and the Phase 25 API. Questions never carry an answer key, reference query or expected rows until the server reveals them. */

export type DbmsDifficulty = "easy" | "medium" | "hard";
export type DbmsMode =
  | "topic" | "mixed" | "interview" | "sql_lab" | "predict_output" | "debug" | "complete"
  | "design_lab" | "transaction_lab" | "nosql_lab" | "timed_mock" | "weak";
export type DbmsFormat = "concept" | "scenario" | "output" | "debug" | "complete" | "query" | "design" | "transaction";
export type DbmsInteraction = "mcq" | "short" | "sql";
export type DbmsDialect = "standard" | "sqlite" | "mysql" | "postgresql" | "oracle" | "sqlserver" | "mongodb" | "dynamodb";
export type CoverageStatus = "implemented" | "partial" | "missing";
export type Outcome = "correct" | "incorrect" | "unanswered";

export interface SyllabusTopic {
  id: string;
  title: string;
  question_count: number;
  by_difficulty: Record<DbmsDifficulty, number>;
  by_format: Partial<Record<DbmsFormat, number>>;
  by_interaction: Partial<Record<DbmsInteraction, number>>;
  status: CoverageStatus;
}
export interface SyllabusUnit {
  id: string;
  code: string;
  title: string;
  summary: string;
  question_count: number;
  topics: SyllabusTopic[];
  topics_implemented: number;
  topics_total: number;
}
export interface SqlEngine {
  engine: string;
  version: string;
  window_functions: boolean;
  right_full_join: boolean;
  dialect: string;
  read_only: boolean;
  limits: { max_sql_chars: number; max_rows: number; max_seconds: number; supported_statements: string[] };
}
export interface Syllabus {
  units: SyllabusUnit[];
  question_total: number;
  min_questions_per_topic: number;
  topics_implemented: number;
  topics_total: number;
  sql_engine: SqlEngine;
}

export interface DatasetColumn { name: string; type: string; primary_key: boolean; not_null: boolean; references: string | null }
export interface DatasetTable { name: string; description: string; columns: DatasetColumn[]; rows: (string | number | null)[][]; row_count: number }
export interface Dataset { id: string; title: string; description: string; tables: DatasetTable[]; indexes: { name: string; table: string; sql: string }[]; ddl: string }

export type Cell = string | number | null;
export interface RunError { kind: string; message: string }
export interface RunResult { ok: boolean; columns: string[]; rows: Cell[][]; row_count: number; truncated: boolean; elapsed_ms: number; error: RunError | null }
export interface ResultPayload { columns: string[]; rows: Cell[][]; row_count: number; truncated: boolean }

export interface ShortPublic { kind: "attrs" | "keys" | "number"; help: string }
export interface SqlPublic { dataset_id: string; starter: string | null; ordered: boolean; check_column_names: boolean; expected_columns: string[] }

export interface McqFeedback { kind: "mcq"; is_correct: boolean; correct_index: number; explanation: string }
export interface ShortFeedback { kind: "short"; is_correct: boolean; answer: string; explanation: string }
export interface SqlFeedback { kind: "sql"; is_correct: boolean; revealed: boolean; reference_sql: string; expected: ResultPayload; explanation: string }
export type Feedback = McqFeedback | ShortFeedback | SqlFeedback;
export interface Verdict { code: string; messages: string[] }

export interface SessionQuestion {
  question_id: string;
  unit_id: string;
  topic_id: string;
  format: DbmsFormat;
  interaction: DbmsInteraction;
  dialect: DbmsDialect;
  difficulty: DbmsDifficulty;
  statement: string;
  code: string | null;
  options: string[];
  dataset_id: string | null;
  est_time_seconds: number;
  tags: string[];
  short: ShortPublic | null;
  sql: SqlPublic | null;
  selected_index: number | null;
  text_answer: string | null;
  sql_answer: string | null;
  marked_for_review: boolean;
  locked: boolean;
  checks: number;
  hints_total: number;
  hints_used: number;
  hints: string[];
  last_check: Verdict | null;
  feedback: Feedback | null;
}

export interface DbmsSession {
  session_id: string;
  mode: DbmsMode;
  status: "in_progress" | "completed";
  difficulty: DbmsDifficulty | null;
  question_count: number;
  requested_count: number;
  unit_ids: string[];
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
  mode: DbmsMode;
  unit_ids?: string[];
  topic_ids?: string[];
  difficulty?: DbmsDifficulty;
  question_count: number;
  timer_minutes?: number;
  immediate_feedback?: boolean;
}

export interface AnswerPayload { selected_index?: number | null; text?: string | null; sql?: string | null; marked_for_review: boolean; time_spent_seconds: number }
export interface SavedAnswer { question_id: string; selected_index: number | null; marked_for_review: boolean; locked: boolean; feedback: Feedback | null; remaining_seconds: number | null }

export interface CheckOutcome {
  question_id: string;
  kind: "short" | "sql";
  correct: boolean;
  locked: boolean;
  checks: number;
  verdict?: Verdict;
  run?: RunResult;
  comparison?: { expected: ResultPayload; actual: ResultPayload } | null;
  feedback: Feedback | null;
  remaining_seconds: number | null;
}
export interface RevealOutcome { question_id: string; locked: boolean; feedback: SqlFeedback; remaining_seconds: number | null }
export interface HintOutcome { question_id: string; hint: string; hint_number: number; hints_total: number; hints: string[] }

export interface TopicPerformance { topic_id: string; topic_title: string; unit_id: string; total: number; correct: number; incorrect: number; unanswered: number; accuracy: number }
export interface RevisionTopic { topic_id: string; topic_title: string; accuracy: number }
export interface ResultQuestion {
  question_id: string;
  unit_id: string;
  topic_id: string;
  format: DbmsFormat;
  interaction: DbmsInteraction;
  dialect: DbmsDialect;
  difficulty: DbmsDifficulty;
  statement: string;
  code: string | null;
  dataset_id: string | null;
  options: string[];
  selected_index: number | null;
  correct_index: number | null;
  outcome: Outcome;
  explanation: string;
  marked_for_review: boolean;
  time_spent_seconds: number;
  hints_used: number;
  text_answer: string | null;
  sql_answer: string | null;
  sql_checks: number;
  revealed: boolean;
  note: string | null;
  verdict: Verdict | null;
  actual: ResultPayload | null;
  correct_answer: string | null;
  reference_sql: string | null;
  expected: ResultPayload | null;
}
export interface DbmsResult {
  session_id: string;
  mode: DbmsMode;
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
  finished_at: string;
  topic_performance: TopicPerformance[];
  revision_topics: RevisionTopic[];
  questions: ResultQuestion[];
  scoring_policy: string;
}

export interface WeakTopic { topic_id: string; topic_title: string; unit_id: string; answered: number; correct: number; accuracy: number; reason: string }
export interface DbmsProgress {
  sessions_completed: number;
  questions_presented: number;
  questions_answered: number;
  correct: number;
  incorrect: number;
  unanswered: number;
  accuracy: number;
  average_seconds_per_answered_question: number | null;
  topic_accuracy: { topic_id: string; topic_title: string; unit_id: string; answered: number; correct: number; presented: number; accuracy: number }[];
  unit_accuracy: { unit_id: string; unit_title: string; answered: number; correct: number; accuracy: number }[];
  difficulty_accuracy: { difficulty: DbmsDifficulty; answered: number; correct: number; accuracy: number }[];
  sql: { questions_answered: number; queries_checked: number; solved: number; solutions_revealed: number; success_rate: number };
  mock_interviews: { session_id: string; score: number; total: number; accuracy: number; time_taken_seconds: number; finished_at: string }[];
  recent_sessions: { session_id: string; mode: DbmsMode; score: number; total: number; accuracy: number; time_taken_seconds: number; finished_at: string }[];
  trend: { session_id: string; accuracy: number; finished_at: string }[];
  improvement_points: number | null;
  weak_topics: WeakTopic[];
  repeated_mistakes: { question_id: string; topic_id: string; topic_title: string; times_incorrect: number }[];
}
export interface Recommendations {
  has_history: boolean;
  weak_topics: WeakTopic[];
  incorrect_question_count: number;
  repeated_mistake_count: number;
  message: string;
  thresholds: { min_answered: number; accuracy_below: number };
}
