import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { getNews, getNewsCategories, getNewsSources } from "@/services/newsService";
import { getApiErrorMessage } from "@/utils/apiError";
import type { NewsArticle, NewsCategoriesResponse, NewsCategoryId, NewsFreshness, NewsSourceInfo } from "@/types/news";

export const PAGE_SIZE = 12;
const SEARCH_DEBOUNCE_MS = 350;
const EMPTY_POLL_MS = 4000;
const EMPTY_POLL_MAX = 5;

export type FeedStatus = "loading" | "ready" | "error";

export interface NewsFilters {
  q: string;
  category: NewsCategoryId | null;
  source: string | null;
}

export const NO_FILTERS: NewsFilters = { q: "", category: null, source: null };

export function hasActiveFilters(f: NewsFilters): boolean {
  return f.q.trim() !== "" || f.category !== null || f.source !== null;
}

/**
 * Loads the public news feed. Typing is debounced, every request is cancellable (a stale response
 * can never overwrite a newer one), and "load more" appends the next page. When the server has an
 * empty cache and is fetching for the first time, the first page is re-requested a few times.
 */
export function useNewsFeed() {
  const [filters, setFilters] = useState<NewsFilters>(NO_FILTERS);
  const [debouncedQ, setDebouncedQ] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [categories, setCategories] = useState<NewsCategoriesResponse | null>(null);
  const [sources, setSources] = useState<NewsSourceInfo[]>([]);
  const [critical, setCritical] = useState<NewsArticle[]>([]);

  // Loading / error are *derived*: a result or failure only counts if it belongs to the request
  // currently wanted (its key). Changing a filter changes the key, so the view reads "loading"
  // immediately and an old response can never be shown for new filters -- without calling
  // setState synchronously inside an effect.
  const requestKey = `${debouncedQ}|${filters.category ?? ""}|${filters.source ?? ""}|${reloadKey}`;
  const [result, setResult] = useState<{ key: string; items: NewsArticle[]; total: number; page: number; hasMore: boolean; freshness: NewsFreshness } | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);
  const [more, setMore] = useState<{ key: string; loading: boolean; error: string | null } | null>(null);
  const moreController = useRef<AbortController | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(filters.q.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [filters.q]);

  const searching = filters.q.trim() !== debouncedQ;

  // First page for the current filters.
  useEffect(() => {
    const controller = new AbortController();
    moreController.current?.abort();
    let pollTimer: ReturnType<typeof setTimeout> | undefined;
    let polls = 0;
    const key = requestKey;
    const unfiltered = !debouncedQ && !filters.category && !filters.source;

    const load = () =>
      getNews({ q: debouncedQ, category: filters.category ?? undefined, source: filters.source ?? undefined, page: 1, limit: PAGE_SIZE }, controller.signal)
        .then((res) => {
          setFailure(null);
          setResult({ key, items: res.items, total: res.total, page: 1, hasMore: res.has_more, freshness: res.freshness });
          if (unfiltered && res.freshness.state === "empty" && res.total === 0 && polls < EMPTY_POLL_MAX) {
            polls += 1;
            pollTimer = setTimeout(load, EMPTY_POLL_MS);
          }
        })
        .catch((e: unknown) => {
          if (axios.isCancel(e) || controller.signal.aborted) return;
          setFailure({ key, message: getApiErrorMessage(e, "We couldn't load the news right now.") });
        });

    void load();
    return () => {
      controller.abort();
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [requestKey, debouncedQ, filters.category, filters.source]);

  // Category counts and the source list. Failure here only hides the extras.
  useEffect(() => {
    const controller = new AbortController();
    getNewsCategories(controller.signal).then(setCategories).catch(() => undefined);
    getNewsSources(controller.signal).then(setSources).catch(() => undefined);
    return () => controller.abort();
  }, [reloadKey]);

  // Critical-severity strip: shown only when the source (NVD) actually scored items critical.
  useEffect(() => {
    const controller = new AbortController();
    getNews({ severity: "critical", limit: 3 }, controller.signal)
      .then((res) => setCritical(res.items.filter((a) => a.severity?.level === "critical")))
      .catch(() => setCritical([]));
    return () => controller.abort();
  }, [reloadKey]);

  const current = result?.key === requestKey ? result : null;
  const failed = failure?.key === requestKey ? failure : null;
  const status: FeedStatus = failed && !current ? "error" : current ? "ready" : "loading";
  const moreState = more?.key === requestKey ? more : null;

  const loadMore = useCallback(() => {
    if (!current || !current.hasMore || moreState?.loading) return;
    const key = requestKey;
    const controller = new AbortController();
    moreController.current = controller;
    setMore({ key, loading: true, error: null });
    getNews({ q: debouncedQ, category: filters.category ?? undefined, source: filters.source ?? undefined, page: current.page + 1, limit: PAGE_SIZE }, controller.signal)
      .then((res) => {
        setResult((prev) => {
          if (!prev || prev.key !== key) return prev;
          const seen = new Set(prev.items.map((a) => a.id));
          return { ...prev, items: [...prev.items, ...res.items.filter((a) => !seen.has(a.id))], page: res.page, hasMore: res.has_more, total: res.total, freshness: res.freshness };
        });
        setMore({ key, loading: false, error: null });
      })
      .catch((e: unknown) => {
        if (axios.isCancel(e) || controller.signal.aborted) return;
        setMore({ key, loading: false, error: getApiErrorMessage(e, "Couldn't load more articles.") });
      });
  }, [current, moreState?.loading, requestKey, debouncedQ, filters.category, filters.source]);

  return {
    filters, setFilters, searching, status, categories, sources, critical, loadMore,
    items: current?.items ?? [], total: current?.total ?? 0, hasMore: current?.hasMore ?? false, freshness: current?.freshness ?? null,
    error: failed?.message ?? null, loadMoreError: moreState?.error ?? null, loadingMore: moreState?.loading ?? false,
    retry: () => { setFailure(null); setReloadKey((k) => k + 1); },
    clearFilters: () => setFilters(NO_FILTERS),
  };
}
