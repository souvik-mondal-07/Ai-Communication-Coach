/**
 * Types for the History & Activity Center (Step 15). They mirror
 * `app.schemas.history` -- a normalized view over the existing session
 * collections, not a separate data store.
 */

export type HistoryActivityType =
  | "cybersecurity_practice"
  | "ctf"
  | "communication"
  | "interview"
  | "pressure_training"
  | "voice_conversation";

export type HistoryStatus = "completed" | "in_progress" | "abandoned";

export type HistorySort = "newest" | "oldest";

export type DateRangePreset = "all" | "today" | "7d" | "30d" | "custom";

export interface HistoryActivity {
  id: string;
  type: HistoryActivityType;
  type_label: string;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  score: number | null;
  status: HistoryStatus;
  metadata: Record<string, string | number | boolean | null>;
}

export interface HistoryListResponse {
  items: HistoryActivity[];
  page: number;
  limit: number;
  total: number;
  has_next: boolean;
}

export interface HistoryTypeCount {
  type: HistoryActivityType;
  label: string;
  count: number;
}

export interface HistorySummary {
  total: number;
  types: HistoryTypeCount[];
}

export interface HistoryDetail<T = unknown> {
  activity: HistoryActivity;
  /** The existing, client-safe session payload for this activity type. */
  detail: T;
}

/** What the user has selected on the History page. */
export interface HistoryFilters {
  type: HistoryActivityType | "all";
  search: string;
  range: DateRangePreset;
  /** yyyy-mm-dd, only used when range === "custom". */
  customStart: string;
  customEnd: string;
  sort: HistorySort;
}

/** Query parameters understood by `GET /history`. */
export interface HistoryQuery {
  type?: HistoryActivityType;
  search?: string;
  start_date?: string;
  end_date?: string;
  sort?: HistorySort;
  page: number;
  limit: number;
}
