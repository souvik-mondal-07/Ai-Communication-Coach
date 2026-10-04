/**
 * Types for the adaptive personalization layer (Step 16). Mirrors the
 * response shapes of `app.api.routes.personalization`.
 */

export type DataStatus = "none" | "limited" | "sufficient";
export type RecommendationBasis = "performance" | "profile";
export type RecommendationKind = "practice" | "interview" | "communication" | "pressure" | "ctf";
export type TopicTrend = "improving" | "stable" | "declining" | "insufficient_data";
export type PersonalizationLevel = "beginner" | "intermediate" | "advanced";

export interface Strength {
  topic: string;
  key: string;
  average_score: number;
  trend: TopicTrend;
  evidence: string[];
}

export interface Weakness {
  topic: string;
  key: string;
  severity: "low" | "medium" | "high";
  average_score: number;
  trend: TopicTrend;
  evidence: string[];
}

export interface Recommendation {
  type: RecommendationKind;
  topic: string;
  topic_key: string;
  topic_slug: string | null;
  title: string;
  difficulty: PersonalizationLevel | null;
  difficulty_reason: string | null;
  reasons: string[];
  basis: RecommendationBasis;
  priority: "low" | "medium" | "high";
  route: string;
}

export interface LearningFocus {
  topic: string;
  title: string;
  basis: RecommendationBasis;
  reasons: string[];
}

export interface RecommendationsResponse {
  data_status: DataStatus;
  message: string | null;
  current_focus: LearningFocus | null;
  recommended_difficulty: PersonalizationLevel;
  recommended_activity: Recommendation | null;
  recommendations: Recommendation[];
}

export interface WeaknessesResponse {
  data_status: DataStatus;
  message: string | null;
  strengths: Strength[];
  weaknesses: Weakness[];
  other_weaknesses: { area: string; source: string; severity: string; average_score: number; attempts: number }[];
}

export interface PersonalizationProfile extends RecommendationsResponse, WeaknessesResponse {
  user_level: PersonalizationLevel;
  difficulty_preference: string;
  career_goal: string | null;
  interests: string[];
  response_style: string;
  learning_style: string;
  interview_focus: string[];
  recommended_topics: string[];
  last_updated: string;
}
