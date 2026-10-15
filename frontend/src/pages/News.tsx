import { useEffect } from "react";
import { Link } from "react-router-dom";
import { LogIn, Newspaper } from "lucide-react";
import { Button } from "@/components/ui/button";
import { buttonVariants } from "@/components/ui/button-variants";
import { PageHeader } from "@/components/ui/page-header";
import { ArticleCard } from "@/features/news/ArticleCard";
import { CriticalStrip } from "@/features/news/CriticalStrip";
import { FreshnessNotice, NewsEmpty, NewsError, NewsSkeleton } from "@/features/news/NewsStates";
import { NewsToolbar } from "@/features/news/NewsToolbar";
import { hasActiveFilters, useNewsFeed } from "@/features/news/useNewsFeed";
import { APP_FALLBACK_TITLE } from "@/components/common/navigation";
import { useAuthStore } from "@/store/authStore";

/** Public cybersecurity news. Reachable by anyone; sign-in is offered, never required. */
export default function News() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const feed = useNewsFeed();
  const filtered = hasActiveFilters(feed.filters);
  const labels = Object.fromEntries((feed.categories?.categories ?? []).map((c) => [c.id, c.label]));

  useEffect(() => {
    document.title = `Cybersecurity News · ${APP_FALLBACK_TITLE}`;
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Newspaper}
        title="Cybersecurity News"
        description="Headlines and advisories from CISA, NIST, the UK NCSC and respected security publications — gathered in one place so you can follow what's happening and click through to the original."
      />

      {!isAuthenticated && (
        <aside className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-card)] border border-border bg-surface-raised/60 px-4 py-3">
          <p className="text-sm text-text-secondary">Reading is free and needs no account. Want a personal AI mentor, practice and progress tracking?</p>
          <div className="flex gap-2">
            <Link to="/login" className={buttonVariants({ variant: "secondary", size: "sm" })}><LogIn size={14} aria-hidden="true" /> Log in</Link>
            <Link to="/register" className={buttonVariants({ variant: "primary", size: "sm" })}>Create free account</Link>
          </div>
        </aside>
      )}

      <NewsToolbar filters={feed.filters} onChange={feed.setFilters} categories={feed.categories} sources={feed.sources} searching={feed.searching} />

      {feed.freshness && feed.status !== "error" && <FreshnessNotice freshness={feed.freshness} />}

      {!filtered && feed.status === "ready" && <CriticalStrip items={feed.critical} />}

      <section aria-label="Articles" aria-busy={feed.status === "loading"}>
        {feed.status === "loading" && <NewsSkeleton />}
        {feed.status === "error" && <NewsError message={feed.error ?? "We couldn't load the news right now."} onRetry={feed.retry} />}
        {feed.status === "ready" && feed.items.length === 0 && (
          <NewsEmpty filtered={filtered} searchTerm={feed.filters.q.trim() || undefined} coldStart={feed.freshness?.state === "empty" && feed.freshness.refreshing} onClear={feed.clearFilters} />
        )}
        {feed.status === "ready" && feed.items.length > 0 && (
          <>
            <p className="mb-3 text-xs text-text-muted" aria-live="polite">
              {feed.total} article{feed.total === 1 ? "" : "s"}{filtered ? " match your filters" : ""}
            </p>
            <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {feed.items.map((a) => (
                <li key={a.id} className="animate-fade-in">
                  <ArticleCard article={a} categoryLabel={labels[a.category]} />
                </li>
              ))}
            </ul>
            <div className="mt-6 flex flex-col items-center gap-2">
              {feed.loadMoreError && <p role="alert" className="text-sm text-danger">{feed.loadMoreError}</p>}
              {feed.hasMore ? (
                <Button variant="secondary" onClick={feed.loadMore} disabled={feed.loadingMore}>
                  {feed.loadingMore ? "Loading…" : feed.loadMoreError ? "Try again" : "Load more articles"}
                </Button>
              ) : (
                <p className="text-xs text-text-muted">You&apos;ve reached the end of the articles we have.</p>
              )}
            </div>
          </>
        )}
      </section>

      <p className="text-xs leading-relaxed text-text-muted">
        Categories are assigned automatically from headlines and tags, so a few may be imperfect. Severity labels appear only when the source (NIST NVD) published a score. Summaries are the publishers&apos; own excerpts.
      </p>
    </div>
  );
}
