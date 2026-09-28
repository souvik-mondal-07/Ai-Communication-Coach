/**
 * Types for the Progress & Personal AI Profile feature (Step 11). These
 * mirror the backend's response shapes from `app.api.routes.progress` --
 * see `app/services/progress/*` for how each field is computed.
 */

export type SkillStatus = "weak" | "developing" | "strong";
export type SkillLevel = "beginner" | "developing" | "intermediate" | "proficient" | "advanced";
export type Confidence = "low" | "medium" | "high";
export type Severity = "low" | "medium" | "high";
export type Priority = "low" | "medium" | "high";
export type RecommendationType = "practice" | "ctf" | "communication" | "interview" | "pressure";
export type Trend = "improving" | "stable" | "declining" | "insufficient_data";
export type TrendPeriod = "7d" | "30d" | "90d";
export type TrendDimension = "technical" | "communication" | "interview" | "pressure" | "overall";

export interface SessionCounts {
  total: number;
  completed: number;
}

export interface OverviewSessionCounts {
  practice_sessions: SessionCounts;
  ctf_sessions: SessionCounts;
  communication_sessions: SessionCounts;
  interview_sessions: SessionCounts;
  pressure_sessions: SessionCounts;
}

export interface SkillBreakdownRow {
  skill: string;
  category: string;
  average_score: number;
  attempts: number;
  successful_attempts: number;
  status: SkillStatus;
  level: SkillLevel;
  confidence: Confidence;
  last_practiced_at: string | null;
  source: "cybersecurity_practice";
}

export interface CtfBreakdownRow {
  category: string;
  attempts: number;
  completed: number;
  completion_rate: number;
  average_hints_used: number;
  last_activity_at: string | null;
}

export interface CommunicationSummary {
  attempts: number;
  overall_score: number;
  clarity_score: number;
  grammar_score: number;
  vocabulary_score: number;
  professionalism_score: number;
  confidence_score: number;
  relevance_score: number;
  conversation_flow_score: number;
  last_session_at: string | null;
}

export interface InterviewTopicBreakdownRow {
  topic: string;
  label: string;
  average_score: number;
  sessions: number;
  questions: number;
}

export interface InterviewSummary {
  attempts: number;
  overall_score: number;
  technical_score: number;
  communication_score: number;
  topic_breakdown: InterviewTopicBreakdownRow[];
  last_session_at: string | null;
}

export interface PressureSummary {
  attempts: number;
  overall_score: number;
  pressure_handling_score: number | null;
  response_control_score: number | null;
  recent_indicators: string[];
  last_session_at: string | null;
}

export interface ActivityItem {
  type: "practice" | "ctf" | "communication" | "interview" | "pressure";
  label: string;
  category: string | null;
  score: number | null;
  completed_at: string;
}

export interface WeaknessEvidence {
  average_score: number;
  attempts: number;
  threshold: number;
  minimum_attempts: number;
}

export interface Weakness {
  _id: string;
  user_id: string;
  area: string;
  skill: string;
  source: "cybersecurity_practice" | "interview" | "communication" | "pressure";
  severity: Severity;
  evidence: WeaknessEvidence;
  detected_at: string;
  last_updated_at: string;
}

export interface Recommendation {
  _id: string;
  user_id: string;
  type: RecommendationType;
  area: string;
  topic: string;
  priority: Priority;
  reason: string;
  created_at: string;
  completed: boolean;
  completed_at: string | null;
}

export interface ProgressOverview {
  session_counts: OverviewSessionCounts;
  has_activity: boolean;
  cybersecurity_performance: {
    categories_practiced: number;
    average_score: number | null;
  };
  communication_performance: CommunicationSummary | null;
  interview_performance: InterviewSummary | null;
  pressure_performance: PressureSummary | null;
  recent_activity: ActivityItem[];
  strengths: string[];
  weaknesses: Weakness[];
  recommendations: Recommendation[];
}

export interface SkillsResponse {
  cybersecurity_skills: SkillBreakdownRow[];
  ctf_activity: CtfBreakdownRow[];
}

export interface TrendPoint {
  period: string;
  average_score: number;
  count: number;
}

export interface TrendSeries {
  points: TrendPoint[];
  trend: Trend;
}

export interface TrendsResponse {
  period: TrendPeriod;
  dimensions: Record<TrendDimension, TrendSeries>;
}

export interface TechnicalProfile {
  strong_areas: string[];
  developing_areas: string[];
  weak_areas: string[];
}

export interface CommunicationProfile {
  strengths: string[];
  improvement_areas: string[];
}

export interface InterviewProfile {
  strengths: string[];
  improvement_areas: string[];
}

export interface PressureProfile {
  observed_indicators: string[];
  improvement_areas: string[];
}

export interface AiProfileSummary {
  summary: string;
  strengths: string[];
  improvement_areas: string[];
  suggested_next_focus: string[];
}

export interface PersonalProfile {
  user_id: string;
  technical_profile: TechnicalProfile;
  communication_profile: CommunicationProfile;
  interview_profile: InterviewProfile;
  pressure_profile: PressureProfile;
  learning_preferences: { preferred_difficulty: string };
  recent_focus: string[];
  recommended_focus: string[];
  ai_summary: AiProfileSummary | null;
  updated_at: string | null;
}

export interface RecalculateResult {
  skills_recalculated: number;
  weaknesses_detected: number;
  recommendations_active: number;
  ai_summary_generated: boolean;
  profile_updated: boolean;
}
