/** Step 19 -- daily practice types (mirror backend/app/schemas/daily_practice.py). */

export type TaskKind = "cybersecurity" | "communication" | "interview";
export type TaskStatus = "pending" | "in_progress" | "completed";

export interface DailyTask {
  task_id: TaskKind;
  kind: TaskKind;
  title: string;
  description: string;
  why: string[];
  est_minutes: number;
  route: string;
  /** Exactly what the owning module's start call needs (see dailyPracticeLauncher). */
  config: Record<string, unknown>;
  status: TaskStatus;
  session_id: string | null;
  score: number | null;
  minutes: number | null;
}

export interface DailySummary {
  technical_score: number | null;
  communication_score: number | null;
  topics: string[];
  minutes_practiced: number;
  streak: number;
  results: { task_id: string; title: string; score: number | null; minutes: number | null }[];
  recommended_next: string | null;
}

export interface DailyPlan {
  date: string;
  status: TaskStatus;
  goal_minutes: number;
  difficulty: string;
  focus: { title: string; topic: string; basis: string };
  rationale: string[];
  tasks: DailyTask[];
  started_at: string | null;
  completed_at: string | null;
  completion: "full" | "partial" | null;
  summary: DailySummary | null;
}

export interface DailyGoal {
  goal_minutes: number;
  minutes_done: number;
  tasks_total: number;
  tasks_done: number;
}

export interface Streak {
  current_streak: number;
  longest_streak: number;
  last_practice_date: string | null;
  total_active_days: number;
  practiced_today: boolean;
  at_risk: boolean;
  timezone: string;
}

export interface DailyPracticeState {
  enabled: boolean;
  rest_day: boolean;
  date: string;
  timezone: string;
  plan: DailyPlan | null;
  goal: DailyGoal | null;
  streak: Streak;
  unread_notifications: number;
}
