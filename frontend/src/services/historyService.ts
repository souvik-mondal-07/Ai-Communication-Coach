import { api } from "@/services/api";
import type {
  HistoryActivityType,
  HistoryDetail,
  HistoryListResponse,
  HistoryQuery,
  HistorySummary,
} from "@/types/history";

/**
 * Client for the History & Activity Center. The user is identified by the
 * JWT alone -- no user id is ever sent.
 */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export async function getHistory(query: HistoryQuery, signal?: AbortSignal): Promise<HistoryListResponse> {
  const { data } = await api.get<ApiEnvelope<HistoryListResponse>>("/history", {
    params: query,
    signal,
  });
  return data.data;
}

export async function getHistorySummary(signal?: AbortSignal): Promise<HistorySummary> {
  const { data } = await api.get<ApiEnvelope<HistorySummary>>("/history/summary", { signal });
  return data.data;
}

export async function getActivity<T = unknown>(
  type: HistoryActivityType,
  id: string,
  signal?: AbortSignal
): Promise<HistoryDetail<T>> {
  const { data } = await api.get<ApiEnvelope<HistoryDetail<T>>>(
    `/history/${type}/${encodeURIComponent(id)}`,
    { signal }
  );
  return data.data;
}
