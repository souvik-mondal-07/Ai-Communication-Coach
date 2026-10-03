import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ActivityCard } from "@/features/history/ActivityCard";
import { HistoryEmpty, HistoryError, HistorySkeleton } from "@/features/history/HistoryStates";
import { HistoryToolbar } from "@/features/history/HistoryToolbar";
import { SummaryTiles } from "@/features/history/SummaryTiles";
import {
  DEFAULT_FILTERS,
  hasActiveFilters,
  isInvalidCustomRange,
  toQuery,
} from "@/features/history/historyMeta";
import * as historyService from "@/services/historyService";
import type { HistoryFilters, HistoryListResponse, HistorySummary } from "@/types/history";

const SEARCH_DEBOUNCE_MS = 350;

export default function History() {
  const [filters, setFilters] = useState<HistoryFilters>(DEFAULT_FILTERS);
  const [searchText, setSearchText] = useState("");
  const [page, setPage] = useState(1);

  const [summary, setSummary] = useState<HistorySummary | null>(null);
  const [summaryFailed, setSummaryFailed] = useState(false);
  const [list, setList] = useState<HistoryListResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [reloadKey, setReloadKey] = useState(0);

  // Changing any filter returns to page 1 (done in one place so they can't drift apart).
  const updateFilters = useCallback((patch: Partial<HistoryFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
    setPage(1);
  }, []);

  // Debounce typing so each keystroke doesn't hit the API.
  const searchTimer = useRef<number | undefined>(undefined);
  const onSearchText = useCallback(
    (value: string) => {
      setSearchText(value);
      window.clearTimeout(searchTimer.current);
      searchTimer.current = window.setTimeout(() => updateFilters({ search: value }), SEARCH_DEBOUNCE_MS);
    },
    [updateFilters]
  );
  useEffect(() => () => window.clearTimeout(searchTimer.current), []);

  // Overview counts: all-time and independent of the filters below.
  useEffect(() => {
    const controller = new AbortController();
    setSummaryFailed(false);
    historyService
      .getHistorySummary(controller.signal)
      .then(setSummary)
      .catch(() => !controller.signal.aborted && setSummaryFailed(true));
    return () => controller.abort();
  }, [reloadKey]);

  // The list. Aborting the previous request means a slow, stale response can never overwrite a newer one.
  const invalidRange = isInvalidCustomRange(filters);
  useEffect(() => {
    if (invalidRange) return;
    const controller = new AbortController();
    setStatus("loading");
    historyService
      .getHistory(toQuery(filters, page), controller.signal)
      .then((data) => {
        setList(data);
        setStatus("ready");
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus("error");
      });
    return () => controller.abort();
  }, [filters, page, invalidRange, reloadKey]);

  const retry = () => setReloadKey((k) => k + 1);
  const clearFilters = () => {
    setSearchText("");
    updateFilters({ search: "", range: "all", customStart: "", customEnd: "" });
  };

  const items = list?.items ?? [];
  const totalPages = list ? Math.max(1, Math.ceil(list.total / list.limit)) : 1;

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <header>
        <h1 className="font-display text-xl font-semibold text-text-primary">History &amp; Activity</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Everything you've practiced, in one place. Open any session to review it.
        </p>
      </header>

      {summary && summary.total > 0 && <SummaryTiles summary={summary} />}
      {summaryFailed && !summary && (
        <p className="text-xs text-text-muted">Your totals couldn't be loaded, but your activity is still shown below.</p>
      )}

      {/* With no activity at all there is nothing to filter, so skip the toolbar. */}
      {(summary === null || summary.total > 0) && (
        <HistoryToolbar
          filters={filters}
          summary={summary}
          searchText={searchText}
          onSearchText={onSearchText}
          onChange={updateFilters}
        />
      )}

      <section aria-label="Activity list" aria-busy={status === "loading"}>
        {invalidRange ? (
          <p className="text-sm text-text-muted">Choose a valid date range to see activity.</p>
        ) : status === "error" ? (
          <HistoryError onRetry={retry} />
        ) : status === "loading" && !list ? (
          <HistorySkeleton />
        ) : items.length === 0 && status === "ready" ? (
          <HistoryEmpty type={filters.type} filtered={hasActiveFilters(filters)} onClearFilters={clearFilters} />
        ) : (
          <div className="space-y-3">
            <ul className={status === "loading" ? "space-y-3 opacity-60 transition-opacity" : "space-y-3"}>
              {items.map((activity) => (
                <li key={`${activity.type}-${activity.id}`}>
                  <ActivityCard activity={activity} />
                </li>
              ))}
            </ul>

            {list && list.total > list.limit && (
              <nav aria-label="Pagination" className="flex items-center justify-between gap-3 pt-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page <= 1 || status === "loading"}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft size={14} aria-hidden="true" /> Previous
                </Button>
                <p className="text-xs text-text-muted">
                  Page {list.page} of {totalPages} · {list.total} activities
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!list.has_next || status === "loading"}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next <ChevronRight size={14} aria-hidden="true" />
                </Button>
              </nav>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
