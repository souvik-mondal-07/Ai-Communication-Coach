/** Mirrors `app.schemas.dsa` (Phase 24). Questions never carry an answer key, reference solution or hidden test until a session is submitted. */

export type DsaDifficulty = "easy" | "medium" | "hard";
export type DsaMode = "topic" | "interview" | "tracing" | "complexity" | "coding" | "timed_mock" | "weak";
export type DsaFormat = "conceptual" | "scenario" | "output" | "trace" | "complexity" | "coding";
export type DsaInteraction = "mcq" | "code";
export type CodingType = "fill_line" | "fix_bug" | "write_function";
export type CoverageStatus = "implemented" | "partial" | "missing";
export type Outcome = "correct" | "incorrect" | "unanswered" | "ungraded";
export type SelfVerdict = "passed" | "failed" | "partial";

export interface SyllabusSubtopic {
  id: string;
  title: string;
  question_count: number;
  by_difficulty: Record<DsaDifficulty, number>;
  by_format: Partial<Record<DsaFormat, number>>;
  auto_graded: number;
  self_assessed_code: number;
  status: CoverageStatus;
}

export interface SyllabusTopic {
  id: string;
  code: string;
  title: string;
  summary: string;
  question_count: number;
  subtopics: SyllabusSubtopic[];
  items: { text: string; subtopic_ids: string[]; question_count: number }[];
  subtopics_implemented: number;
  subtopics_total: number;
  status: CoverageStatus;
}

export interface Syllabus {
  topics: SyllabusTopic[];
  totals: {
    topics: number;
    subtopics: number;
    subtopics_implemented: number;
    questions: number;
    by_format: Record<DsaFormat, number>;
    min_questions_per_subtopic: number;
  };
  execution: { automated_code_execution: boolean; mode: string; message: string };
}

export interface TestCase {
  label: string;
  args: unknown[];
  expected: unknown;
}
export interface FullTestCase extends TestCase {
  visible: boolean;
  edge: boolean;
}

export interface PublicCoding {
  function_name: string;
  template: string;
  sample_io: string | null;
  visible_tests: TestCase[];
  hidden_test_count: number;
}

export interface TraceStep {
  label: string;
  state: string;
}

export type Complexity = Record<string, string>;

export type AnswerFeedback =
  | { kind: "mcq"; is_correct: boolean; correct_index: number; explanation: string; complexity: Complexity | null; trace: TraceStep[] | null }
  | { kind: "code"; explanation: string; reference_solution: string; test_cases: FullTestCase[]; complexity: Complexity | null; execution_note: string };

export interface SessionQuestion {
  question_id: string;
  topic_id: string;
  subtopic_id: string;
  format: DsaFormat;
  interaction: DsaInteraction;
  coding_type: CodingType | null;
  difficulty: DsaDifficulty;
  statement: string;
  code: string | null;
  options: string[];
  constraints: string | null;
  est_time_seconds: number;
  coding: PublicCoding | null;
  selected_index: number | null;
  code_answer: string | null;
  marked_for_review: boolean;
  locked: boolean;
  hints: string[];
  feedback: AnswerFeedback | null;
}

export interface DsaSession {
  session_id: string;
  mode: DsaMode;
  status: "in_progress" | "completed";
  difficulty: DsaDifficulty | null;
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
  mode: DsaMode;
  topic_ids: string[];
  subtopic_ids: string[];
  difficulty?: DsaDifficulty;
  question_count: number;
  timer_minutes?: number;
  immediate_feedback?: boolean;
}

export interface AnswerPayload {
  selected_index?: number | null;
  code?: string | null;
  reveal?: boolean;
  marked_for_review: boolean;
  time_spent_seconds: number;
}

export interface SavedAnswer {
  question_id: string;
  selected_index: number | null;
  code_answer: string | null;
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
  format: DsaFormat;
  interaction: DsaInteraction;
  coding_type: CodingType | null;
  difficulty: DsaDifficulty;
  statement: string;
  code: string | null;
  options: string[];
  selected_index: number | null;
  correct_index: number | null;
  code_answer: string | null;
  outcome: Outcome;
  explanation: string;
  complexity: Complexity | null;
  trace: TraceStep[] | null;
  reference_solution: string | null;
  test_cases: FullTestCase[] | null;
  self_assessment: SelfVerdict | null;
  execution_note: string | null;
  marked_for_review: boolean;
  time_spent_seconds: number;
}

export interface RevisionTopic {
  topic_id: string;
  topic_title: string;
  accuracy: number;
  subtopics: { subtopic_id: string; title: string }[];
}

export interface DsaResult {
  session_id: string;
  mode: DsaMode;
  status: "completed";
  total_questions: number;
  graded_questions: number;
  ungraded_questions: number;
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
  revision_topics: RevisionTopic[];
  complexity_summary: { question_id: string; subtopic_id: string; subtopic_title: string; statement: string; complexity: Complexity }[];
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

export interface DsaProgress {
  sessions_completed: number;
  questions_presented: number;
  questions_answered: number;
  correct: number;
  incorrect: number;
  unanswered: number;
  ungraded_code: number;
  accuracy: number;
  average_seconds_per_question: number | null;
  topic_accuracy: { topic_id: string; topic_title: string; answered: number; correct: number; presented: number; accuracy: number }[];
  difficulty_accuracy: { difficulty: DsaDifficulty; answered: number; correct: number; accuracy: number }[];
  recent_sessions: { session_id: string; mode: DsaMode; score: number; total: number; graded: number; accuracy: number; time_taken_seconds: number; finished_at: string }[];
  trend: { session_id: string; accuracy: number; finished_at: string }[];
  improvement_points: number | null;
  weak_topics: WeakTopic[];
  attempts_scanned_limit: number;
}

export interface Recommendations {
  has_history: boolean;
  weak_topics: WeakTopic[];
  incorrect_question_count: number;
  message: string;
  thresholds: { min_answered: number; accuracy_below: number };
}
