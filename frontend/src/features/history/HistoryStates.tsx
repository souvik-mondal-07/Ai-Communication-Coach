import { History as HistoryIcon, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { HistoryActivityType } from "@/types/history";
import { TYPE_META } from "@/features/history/historyMeta";

export function HistorySkeleton() {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">Loading your activity...</span>
      <p className="text-sm text-text-muted" aria-hidden="true">
        Loading your activity...
      </p>
      {Array.from({ length: 5 }, (_, i) => (
        <div
          key={i}
          aria-hidden="true"
          className="flex animate-pulse items-center gap-3 rounded-[var(--radius-panel)] border border-border bg-surface p-4"
        >
          <div className="h-10 w-10 rounded-[var(--radius-panel)] bg-surface-raised" />
          <div className="flex-1 space-y-2">
            <div className="h-2.5 w-24 rounded bg-surface-raised" />
            <div className="h-3.5 w-2/3 rounded bg-surface-raised" />
            <div className="h-2.5 w-1/3 rounded bg-surface-raised" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function HistoryError({ onRetry }: { onRetry: () => void }) {
  return (
    <Card>
      <CardContent className="space-y-3 py-8 text-center" role="alert">
        <p className="text-sm font-medium text-text-primary">Unable to load your activity.</p>
        <p className="text-sm text-text-muted">Please try again.</p>
        <Button variant="secondary" onClick={onRetry}>
          <RefreshCw size={14} aria-hidden="true" /> Retry
        </Button>
      </CardContent>
    </Card>
  );
}

interface EmptyProps {
  /** The selected category, or "all". */
  type: HistoryActivityType | "all";
  /** True when search/date filters (not an empty account) caused the empty result. */
  filtered: boolean;
  onClearFilters: () => void;
}

export function HistoryEmpty({ type, filtered, onClearFilters }: EmptyProps) {
  if (filtered) {
    return (
      <Card>
        <CardContent className="space-y-3 py-10 text-center">
          <p className="text-sm font-medium text-text-primary">No activity matches your filters.</p>
          <p className="text-sm text-text-muted">Try a different search or date range.</p>
          <Button variant="secondary" onClick={onClearFilters}>
            Clear filters
          </Button>
        </CardContent>
      </Card>
    );
  }

  const meta = type === "all" ? null : TYPE_META[type];
  return (
    <Card>
      <CardContent className="space-y-3 py-10 text-center">
        <HistoryIcon size={28} className="mx-auto text-text-muted" aria-hidden="true" />
        <p className="text-sm font-medium text-text-primary">{meta ? meta.empty.title : "No activity yet."}</p>
        <p className="text-sm text-text-muted">
          {meta ? meta.empty.hint : "Complete a practice, interview, or conversation and it will show up here."}
        </p>
        <Link
          to={meta ? meta.modulePath : "/cybersecurity"}
          className="inline-flex h-9 items-center rounded-[var(--radius-panel)] bg-signal px-4 text-sm font-medium text-[#08120f] hover:bg-signal/90"
        >
          {meta ? meta.empty.cta : "Start practicing"}
        </Link>
      </CardContent>
    </Card>
  );
}
