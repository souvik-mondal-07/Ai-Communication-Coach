import { api } from "@/services/api";
import type {
  PersonalProfile,
  ProgressOverview,
  RecalculateResult,
  Recommendation,
  SkillsResponse,
  TrendPeriod,
  TrendsResponse,
  Weakness,
} from "@/types/progress";

/**
 * Client for `/api/v1/progress/...`. Only FastAPI is called -- every number
 * shown here comes from the backend's deterministic aggregation over
 * existing session data, never computed client-side (see
 * `app/services/progress/*`).
 */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export async function getOverview(): Promise<ProgressOverview> {
  const { data } = await api.get<ApiEnvelope<ProgressOverview>>("/progress/overview");
  return data.data;
}

export async function getSkills(): Promise<SkillsResponse> {
  const { data } = await api.get<ApiEnvelope<SkillsResponse>>("/progress/skills");
  return data.data;
}

export async function getTrends(period: TrendPeriod = "30d"): Promise<TrendsResponse> {
  const { data } = await api.get<ApiEnvelope<TrendsResponse>>("/progress/trends", {
    params: { period },
  });
  return data.data;
}

export async function getWeaknesses(): Promise<Weakness[]> {
  const { data } = await api.get<ApiEnvelope<Weakness[]>>("/progress/weaknesses");
  return data.data;
}

export async function getRecommendations(activeOnly = true): Promise<Recommendation[]> {
  const { data } = await api.get<ApiEnvelope<Recommendation[]>>("/progress/recommendations", {
    params: { active_only: activeOnly },
  });
  return data.data;
}

export async function completeRecommendation(recommendationId: string): Promise<Recommendation> {
  const { data } = await api.post<ApiEnvelope<Recommendation>>(
    `/progress/recommendations/${encodeURIComponent(recommendationId)}/complete`
  );
  return data.data;
}

export async function recalculateProgress(): Promise<RecalculateResult> {
  const { data } = await api.post<ApiEnvelope<RecalculateResult>>("/progress/recalculate");
  return data.data;
}

export async function getProfile(): Promise<PersonalProfile> {
  const { data } = await api.get<ApiEnvelope<PersonalProfile>>("/progress/profile");
  return data.data;
}
