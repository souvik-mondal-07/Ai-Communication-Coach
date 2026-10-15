export type NewsCategoryId =
  | "vulnerabilities" | "breaches" | "malware" | "ai-security" | "appsec"
  | "cloud-network" | "bug-bounty" | "tools-research" | "careers" | "general";

export type SeverityLevel = "low" | "medium" | "high" | "critical";

export interface ArticleSeverity {
  level: SeverityLevel;
  score: number | null;
  scheme: string;
  assigned_by: string;
}

export interface NewsArticle {
  id: string;
  title: string;
  /** The source's own excerpt as plain text; null when the source gave none. */
  summary: string | null;
  url: string;
  source_id: string;
  source_name: string;
  category: NewsCategoryId;
  /** When the source says it was published; null when it did not say. */
  published_at: string | null;
  /** When this service first retrieved it. Not a publication date. */
  first_seen_at: string;
  image_url: string | null;
  cve_ids: string[];
  severity: ArticleSeverity | null;
}

export type FreshnessState = "fresh" | "stale" | "degraded" | "empty";

export interface NewsFreshness {
  state: FreshnessState;
  last_successful_refresh_at: string | null;
  last_attempt_at: string | null;
  refreshing: boolean;
  refresh_interval_minutes: number;
  sources_ok: number;
  sources_failed: number;
  message: string | null;
}

export interface NewsListResponse {
  items: NewsArticle[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
  freshness: NewsFreshness;
}

export interface NewsCategoryCount {
  id: NewsCategoryId;
  label: string;
  description: string;
  count: number;
}

export interface NewsCategoriesResponse {
  categories: NewsCategoryCount[];
  total: number;
}

export interface NewsSourceInfo {
  id: string;
  name: string;
  homepage_url: string;
  kind: string;
  status: "ok" | "failed" | "pending" | "disabled";
  last_success_at: string | null;
  last_error: string | null;
  article_count: number;
}

export interface NewsQuery {
  q?: string;
  category?: NewsCategoryId;
  source?: string;
  severity?: SeverityLevel;
  page?: number;
  limit?: number;
}
