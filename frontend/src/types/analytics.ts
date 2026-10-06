/**
 * Types for Advanced Interview & Communication Analytics (Step 18). They mirror
 * `app.api.routes.analytics`; every figure is computed by the backend from stored
 * sessions. `null` always means "no data" -- the UI renders it as N/A, never 0.
 */

export type AnalyticsRange = "7d" | "30d" | "90d" | "all";
export type DataStatus = "none" | "early" | "sufficient";
export type Direction = "improving" | "stable" | "declining" | "insufficient_data";
export type Band = "strong" | "developing" | "weak" | null;
export type ChangeLabel =
  | "Significant improvement"
  | "Improving"
  | "Stable"
  | "Slight decline"
  | "Needs attention"
  | null;

export interface AnalyticsMeta {
  range: string;
  start: string | null;
  end: string;
  truncated: boolean;
  data: { status: DataStatus; message: string | null; sessions: number };
}

export interface Comparison {
  available: boolean;
  previous: number | null;
  current: number | null;
  change: number | null;
  label: ChangeLabel;
  previous_samples: number;
  current_samples: number;
  higher_is_better: boolean;
}

export interface ReadinessComponent {
  label: string;
  score: number;
  samples: number;
  weight: number;
  effective_weight?: number;
}

export interface Readiness {
  available: boolean;
  score: number | null;
  band: string | null;
  coverage: number;
  message: string | null;
  detail: string | null;
  formula: Record<string, number>;
  components: ReadinessComponent[];
  missing_components: { key: string; label: string; samples: number; needed: number }[];
}

export interface OverviewData extends AnalyticsMeta {
  readiness: Readiness;
  scores: { technical: number | null; communication: number | null; confidence: number | null; overall: number | null };
  counts: { interviews: number; pressure: number; communication: number; practice: number };
  comparison:
    | { available: false; reason: string }
    | { available: true; technical: Comparison; communication: Comparison; overall: Comparison; confidence: Comparison };
}

export interface TrendPoint {
  period: string;
  value: number | null;
  samples: number;
}
export interface TrendSeries {
  label: string;
  higher_is_better: boolean;
  points: TrendPoint[];
  direction: Direction;
}
export interface TrendsData extends AnalyticsMeta {
  granularity: "day" | "week" | "month";
  series: Record<string, TrendSeries>;
}

export interface ModeRow {
  mode: string;
  label: string;
  sessions: number;
  overall_score: number | null;
  technical_score: number | null;
  communication_score: number | null;
  band: Band;
  reliable: boolean;
}
export interface DomainRow {
  domain: string;
  score: number | null;
  band: Band;
  questions: number;
}
export interface DomainsData extends AnalyticsMeta {
  domains: DomainRow[];
  insufficient_data: DomainRow[];
  strongest: DomainRow[];
  weakest: DomainRow[];
  modes: ModeRow[];
}

export interface Weakness {
  id: string;
  label: string;
  samples: number;
  occurrences: number;
  rate: number;
  severity: "low" | "medium" | "high";
  evidence: string;
}
export interface CommunicationData extends AnalyticsMeta {
  dimensions: { key: string; score: number; band: Band }[];
  samples: { answers: number; communication_sessions: number };
  structure: { by_kind: { kind: string; answers: number; structure_score: number | null; assessed_answers: number; marker_coverage: number | null }[]; note: string };
  length:
    | { available: false; answers: number }
    | {
        available: true;
        answers: number;
        average_words: number;
        min_words: number;
        max_words: number;
        average_duration_seconds: number | null;
        distribution: Record<"too_short" | "appropriate" | "long" | "very_long", number>;
        note: string;
      };
  weaknesses: Weakness[];
}

export interface SpeakingMetrics {
  spoken_answers: number;
  words_per_minute: number | null;
  filler_per_100_words: number | null;
  pauses_per_minute: number | null;
  long_pauses: number | null;
  average_pause_seconds: number | null;
  average_answer_seconds: number | null;
}
export interface SpeakingData extends AnalyticsMeta {
  available: boolean;
  spoken_answers: number;
  message: string | null;
  metrics: SpeakingMetrics | null;
  not_tracked: string[];
}

export interface PressureSide {
  sessions: number;
  technical: number | null;
  communication: number | null;
  confidence: number | null;
  words_per_minute: number | null;
  filler_per_100_words: number | null;
}
export interface PressureData extends AnalyticsMeta {
  available: boolean;
  message: string | null;
  comparison_available?: boolean;
  normal: PressureSide | null;
  pressure: PressureSide | null;
  differences: { technical?: number; communication?: number };
  insights: string[];
  pressure_handling_score: number | null;
}

export interface Insight {
  kind: string;
  text: string;
  evidence: string;
}
export interface NextAction {
  weakness: string;
  action: string;
  route: string;
  evidence: string;
}
export interface InsightsData extends AnalyticsMeta {
  insights: Insight[];
  strengths: string[];
  weaknesses: Weakness[];
  next_actions: NextAction[];
  recommendations: { title: string; route: string; reasons: string[]; priority: string }[];
  ai_summary: string | null;
}
