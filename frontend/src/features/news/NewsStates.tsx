import { Newspaper, SearchX, TriangleAlert, Info, CircleCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { NewsFreshness } from "@/types/news";
import { describeFreshness } from "@/features/news/newsMeta";

/** Placeholder grid shown while the first page loads. */
export function NewsSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div role="status" aria-label="Loading articles" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-card">
          <Skeleton className="h-5 w-24 rounded-full" />
          <Skeleton className="mt-4 h-5 w-full" />
          <Skeleton className="mt-2 h-5 w-4/5" />
          <Skeleton className="mt-4 h-3 w-full" />
          <Skeleton className="mt-2 h-3 w-2/3" />
          <Skeleton className="mt-6 h-3 w-1/2" />
        </div>
      ))}
      <span className="sr-only">Loading articles…</span>
    </div>
  );
}

export function NewsError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-danger/30 bg-danger/5 p-5">
      <ErrorState message={message} onRetry={onRetry} />
      <p className="mt-2 text-xs text-text-muted">Nothing is wrong with your account — the news service just didn&apos;t answer. Try again in a moment.</p>
    </div>
  );
}

interface NewsEmptyProps {
  /** True when a search, category or source filter is applied. */
  filtered: boolean;
  searchTerm?: string;
  coldStart?: boolean;
  onClear: () => void;
}

export function NewsEmpty({ filtered, searchTerm, coldStart, onClear }: NewsEmptyProps) {
  if (filtered) {
    return (
      <EmptyState
        icon={SearchX}
        title={searchTerm ? `No articles match “${searchTerm}”` : "No articles in this view yet"}
        description="Try different words, another category, or clear the filters to see everything we have."
        action={<Button variant="secondary" size="sm" onClick={onClear}>Clear filters</Button>}
      />
    );
  }
  return (
    <EmptyState
      icon={Newspaper}
      title={coldStart ? "Fetching the latest articles…" : "No articles available right now"}
      description={coldStart ? "The first fetch can take a few seconds. This page will update by itself." : "The news sources haven't returned any articles yet. Please check back shortly."}
    />
  );
}

/** One quiet line about freshness. Warns (with text, not just colour) when data may be out of date. */
export function FreshnessNotice({ freshness, now }: { freshness: NewsFreshness; now?: Date }) {
  const { tone, text } = describeFreshness(freshness, now);
  const Icon = tone === "warn" ? TriangleAlert : tone === "ok" ? CircleCheck : Info;
  return (
    <div className="space-y-1">
      <p
        role={tone === "warn" ? "alert" : "status"}
        className={`flex items-start gap-2 text-xs ${tone === "warn" ? "rounded-[var(--radius-panel)] border border-warn/40 bg-warn/10 px-3 py-2 text-warn" : "text-text-muted"}`}
      >
        <Icon size={14} className="mt-px shrink-0" aria-hidden="true" />
        <span>{text}</span>
      </p>
      {freshness.message && freshness.state !== "degraded" && freshness.state !== "empty" && (
        <p className="pl-6 text-xs text-text-muted">{freshness.message}</p>
      )}
    </div>
  );
}
