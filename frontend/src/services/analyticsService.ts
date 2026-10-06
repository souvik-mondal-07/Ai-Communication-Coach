import { api } from "@/services/api";
import type {
  AnalyticsRange,
  CommunicationData,
  DomainsData,
  InsightsData,
  OverviewData,
  PressureData,
  SpeakingData,
  TrendsData,
} from "@/types/analytics";

/** Client for `/api/v1/analytics/...`. Read-only; the backend derives every number from stored sessions. */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

async function fetchSection<T>(path: string, range: AnalyticsRange, extra?: Record<string, unknown>): Promise<T> {
  const { data } = await api.get<ApiEnvelope<T>>(`/analytics/${path}`, { params: { range, ...extra } });
  return data.data;
}

export const getOverview = (range: AnalyticsRange) => fetchSection<OverviewData>("overview", range);
export const getTrends = (range: AnalyticsRange) => fetchSection<TrendsData>("trends", range);
export const getDomains = (range: AnalyticsRange) => fetchSection<DomainsData>("domains", range);
export const getCommunication = (range: AnalyticsRange) => fetchSection<CommunicationData>("communication", range);
export const getSpeaking = (range: AnalyticsRange) => fetchSection<SpeakingData>("speaking", range);
export const getPressure = (range: AnalyticsRange) => fetchSection<PressureData>("pressure", range);
export const getInsights = (range: AnalyticsRange) => fetchSection<InsightsData>("insights", range);
