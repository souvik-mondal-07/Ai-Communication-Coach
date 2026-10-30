// Types for the Python Interview Practice module (Phase 26). They mirror the backend schemas; nothing here is a client-side score.

export type PyMode = "topic" | "mixed" | "interview" | "predict_output" | "trace" | "debug" | "complete" | "coding" | "complexity" | "oop" | "advanced" | "security" | "timed_mock" | "weak";
export type PyDifficulty = "easy" | "medium" | "hard";
export type PyFormat = "concept" | "output" | "trace" | "debug" | "complete" | "coding" | "complexity" | "scenario";
export type PyInteraction = "mcq" | "short" | "code";
export type Outcome = "correct" | "incorrect" | "unanswered";

export interface RunnerStatus {
  available: boolean;
  reason: string | null;
  platform: string;
  python_version: string;
  layers: string[];
  limits: { wall_seconds: number; cpu_seconds: number; memory_mb: number; processes: number; source_chars: number; output_bytes: number; per_case_seconds: number };
}

export interface TopicRow {
  id: string;
  title: string;
  question_count: number;
  by_difficulty: Record<PyDifficulty, number>;
  by_format: Record<string, number>;
  by_interaction: Record<string, number>;
  status: "implemented" | "partial" | "missing";
}
export interface UnitRow { id: string; code: string; title: string; summary: string; question_count: number; topics: TopicRow[]; topics_implemented: number; topics_total: number }
export interface Syllabus { units: UnitRow[]; question_total: number; min_questions_per_topic: number; topics_implemented: number; topics_total: number; runner: RunnerStatus }

export interface CoverageRow {
  unit: string; topic_id: string; topic: string; covers: string; count: number; easy: number; medium: number; hard: number;
  formats: Record<string, number>; interactions: Record<string, number>; status: string; machine_verified: number; manual_review: number;
}
export interface Coverage { rows: CoverageRow[]; gaps: string[]; total_questions: number; machine_verified: number; manual_review: number; topics_implemented: number; topics_total: number; runner: RunnerStatus }

export interface CodeExample { id: number; label: string; input: string; expected: string }
export interface CodeSpecPublic { mode: "function" | "class" | "stdio"; entry: string; signature: string; starter: string; constraints: string[]; examples: CodeExample[]; visible_count: number; hidden_count: number }
export interface ShortPublic { kind: "text" | "number" | "output"; help: string }

export interface TestOutcome { id: number; label: string; visible: boolean; passed: boolean; status: "passed" | "failed" | "error" | "timeout" | "not_run"; message: string | null; stdout: string | null; ms: number | null }
export interface GradeResult {
  verdict: "accepted" | "wrong_answer" | "runtime_error" | "timeout" | "compile_error" | "output_limit" | "runner_error";
  message: string; passed: number; total: number; accepted: boolean; tests: TestOutcome[];
  setup_error: { type: string | null; message: string; line: number | null } | null; wall_ms: number;
}
export interface LastCheck { verdict: string; passed: number; total: number }

export type Feedback =
  | { kind: "mcq"; is_correct: boolean; correct_index: number; explanation: string }
  | { kind: "short"; is_correct: boolean; answer: string; explanation: string }
  | { kind: "code"; is_correct: boolean; revealed: boolean; reference_source: string; time_complexity: string; space_complexity: string; explanation: string };

export interface SessionQuestion {
  question_id: string; unit_id: string; topic_id: string; format: PyFormat; interaction: PyInteraction; difficulty: PyDifficulty;
  title: string | null; statement: string; code: string | null; options: string[]; est_time_seconds: number; tags: string[]; python_version: string | null;
  short: ShortPublic | null; code_spec: CodeSpecPublic | null;
  selected_index: number | null; text_answer: string | null; code_answer: string | null; marked_for_review: boolean; locked: boolean;
  checks: number; runs: number; hints_total: number; hints_used: number; hints: string[]; last_check: LastCheck | null; last_run: LastCheck | null;
  can_reveal: boolean; feedback: Feedback | null;
}

export interface PySession {
  session_id: string; mode: PyMode; status: "in_progress" | "completed"; difficulty: PyDifficulty | null; question_count: number; requested_count: number;
  unit_ids: string[]; topic_ids: string[]; immediate_feedback: boolean; exam_mode: boolean; started_at: string; expires_at: string | null; server_time: string;
  remaining_seconds: number | null; timer_minutes: number | null; questions: SessionQuestion[]; scoring_policy: string;
}
export interface SessionRequest { mode: PyMode; unit_ids?: string[]; topic_ids?: string[]; difficulty?: PyDifficulty; question_count: number; timer_minutes?: number; immediate_feedback?: boolean }

export interface AnswerPayload { selected_index?: number | null; text?: string | null; code?: string | null; marked_for_review: boolean; time_spent_seconds: number }
export interface SavedAnswer { question_id: string; selected_index: number | null; marked_for_review: boolean; locked: boolean; feedback: Feedback | null; remaining_seconds: number | null }
export interface RunOutcome { question_id: string; kind: "run"; result: GradeResult; remaining_seconds: number | null }
export interface CheckOutcome {
  question_id: string; kind: "short" | "code"; correct: boolean; locked: boolean; checks: number; result?: GradeResult; can_reveal?: boolean;
  feedback: Feedback | null; remaining_seconds: number | null;
}
export interface RevealOutcome { question_id: string; locked: boolean; feedback: Feedback; remaining_seconds: number | null }
export interface HintOutcome { question_id: string; hint: string; hint_number: number; hints_total: number; hints: string[] }

export interface TopicPerformance { topic_id: string; topic_title: string; unit_id: string; total: number; correct: number; incorrect: number; unanswered: number; accuracy: number }
export interface RevisionTopic { topic_id: string; topic_title: string; accuracy: number }
export interface ResultQuestion {
  question_id: string; unit_id: string; topic_id: string; format: PyFormat; interaction: PyInteraction; difficulty: PyDifficulty; title: string | null;
  statement: string; code: string | null; python_version: string | null; options: string[]; selected_index: number | null; correct_index: number | null;
  outcome: Outcome; explanation: string; marked_for_review: boolean; time_spent_seconds: number; hints_used: number; text_answer: string | null; code_answer: string | null;
  code_checks: number; tests_passed: number; tests_total: number; revealed: boolean; note: string | null;
  verdict: { verdict: string; passed: number; total: number; message: string } | null;
  correct_answer: string | null; reference_source: string | null; time_complexity: string | null; space_complexity: string | null;
}
export interface PyResult {
  session_id: string; mode: PyMode; status: "completed"; total_questions: number; correct: number; incorrect: number; unanswered: number; score: number; accuracy: number;
  time_taken_seconds: number; average_seconds_per_question: number; auto_submitted: boolean; started_at: string; finished_at: string;
  topic_performance: TopicPerformance[]; revision_topics: RevisionTopic[]; questions: ResultQuestion[]; scoring_policy: string;
}

export interface WeakTopic { topic_id: string; topic_title: string; unit_id: string; answered: number; correct: number; accuracy: number; reason: string }
export interface PyProgress {
  sessions_completed: number; questions_presented: number; questions_answered: number; correct: number; incorrect: number; unanswered: number; accuracy: number;
  average_seconds_per_answered_question: number | null;
  topic_accuracy: { topic_id: string; topic_title: string; unit_id: string; answered: number; correct: number; presented: number; accuracy: number }[];
  unit_accuracy: { unit_id: string; unit_title: string; answered: number; correct: number; accuracy: number }[];
  difficulty_accuracy: { difficulty: PyDifficulty; answered: number; correct: number; accuracy: number }[];
  coding: { questions_answered: number; solved: number; submissions: number; trial_runs: number; tests_passed: number; tests_total: number; solutions_revealed: number; success_rate: number; test_pass_rate: number };
  mock_interviews: { session_id: string; score: number; total: number; accuracy: number; time_taken_seconds: number; finished_at: string }[];
  recent_sessions: { session_id: string; mode: PyMode; score: number; total: number; accuracy: number; time_taken_seconds: number; finished_at: string }[];
  trend: { session_id: string; accuracy: number; finished_at: string }[];
  improvement_points: number | null; weak_topics: WeakTopic[];
  repeated_mistakes: { question_id: string; topic_id: string; topic_title: string; times_incorrect: number }[];
}
export interface Recommendations { has_history: boolean; weak_topics: WeakTopic[]; incorrect_question_count: number; repeated_mistake_count: number; message: string; thresholds: { min_answered: number; accuracy_below: number } }
export interface HistoryItem { session_id: string; mode: PyMode; status: string; started_at: string; finished_at: string | null; question_count: number; unit_ids: string[]; topic_ids: string[]; score: number | null; accuracy: number | null; time_taken_seconds: number | null; timer_minutes: number | null }
export interface HistoryPage { items: HistoryItem[]; page: number; limit: number; total: number; has_next: boolean }
export interface QuestionPage { items: SessionQuestion[]; page: number; limit: number; total: number; has_next: boolean }
