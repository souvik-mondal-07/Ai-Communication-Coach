import { api } from "@/services/api";
import type { NewsCategoriesResponse, NewsListResponse, NewsQuery, NewsSourceInfo } from "@/types/news";

/**
 * Client for the PUBLIC cybersecurity news endpoints. They need no account, so none of these
 * requests carries the bearer token (`skipAuth`), and none can name a URL: the backend only
 * ever fetches from its own fixed list of sources.
 */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

const PUBLIC = { skipAuth: true } as const;

export async function getNews(query: NewsQuery, signal?: AbortSignal): Promise<NewsListResponse> {
  const params = Object.fromEntries(Object.entries(query).filter(([, v]) => v !== undefined && v !== ""));
  const { data } = await api.get<ApiEnvelope<NewsListResponse>>("/news", { params, signal, ...PUBLIC });
  return data.data;
}

export async function getNewsCategories(signal?: AbortSignal): Promise<NewsCategoriesResponse> {
  const { data } = await api.get<ApiEnvelope<NewsCategoriesResponse>>("/news/categories", { signal, ...PUBLIC });
  return data.data;
}

export async function getNewsSources(signal?: AbortSignal): Promise<NewsSourceInfo[]> {
  const { data } = await api.get<ApiEnvelope<{ sources: NewsSourceInfo[] }>>("/news/sources", { signal, ...PUBLIC });
  return data.data.sources;
}
