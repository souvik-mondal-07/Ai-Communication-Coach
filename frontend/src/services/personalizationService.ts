import { api } from "@/services/api";
import type {
  PersonalizationProfile,
  RecommendationsResponse,
  WeaknessesResponse,
} from "@/types/personalization";

/** Client for `/api/v1/personalization/...` (Step 16). Read-only; the user comes from the JWT. */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export async function getPersonalizationProfile(): Promise<PersonalizationProfile> {
  const { data } = await api.get<ApiEnvelope<PersonalizationProfile>>("/personalization/profile");
  return data.data;
}

export async function getRecommendations(): Promise<RecommendationsResponse> {
  const { data } = await api.get<ApiEnvelope<RecommendationsResponse>>("/personalization/recommendations");
  return data.data;
}

export async function getWeaknesses(): Promise<WeaknessesResponse> {
  const { data } = await api.get<ApiEnvelope<WeaknessesResponse>>("/personalization/weaknesses");
  return data.data;
}
