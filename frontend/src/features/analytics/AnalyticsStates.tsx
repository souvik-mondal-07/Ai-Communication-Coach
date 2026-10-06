import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalyticsMeta } from "@/types/analytics";
import type { LoadState } from "./analyticsUtils";

export function Skeleton({ className = "h-24" }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-[var(--radius-panel)] bg-surface-raised ${className}`} />;
}

/** A titled card whose body shows a skeleton while loading, a retryable error, or the data. */
export function SectionCard<T>({
  title,
  state,
  onRetry,
  render,
  description,
}: {
  title: string;
  state: LoadState<T>;
  onRetry: () => void;
  render: (data: T) => React.ReactNode;
  description?: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description ? <p className="mt-1 text-xs text-text-muted">{description}</p> : null}
      </CardHeader>
      <CardContent>
        {state.status === "loading" ? (
          <div role="status" aria-label={`Loading ${title}`} className="space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-28" />
          </div>
        ) : state.status === "error" ? (
          <div role="alert" className="flex flex-wrap items-center gap-3">
            <p className="text-sm text-danger">{state.message}</p>
            <Button variant="secondary" size="sm" onClick={onRetry}>
              <RefreshCw size={14} /> Retry
            </Button>
          </div>
        ) : (
          render(state.data)
        )}
      </CardContent>
    </Card>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-text-muted">{children}</p>;
}

/** Page-level banner: no sessions at all, or "early data". Silent once data is sufficient. */
export function DataBanner({ meta }: { meta: AnalyticsMeta | null }) {
  if (!meta || meta.data.status === "sufficient") {
    return meta?.truncated ? (
      <p className="text-xs text-text-muted">Showing your most recent sessions only (the range contains more than the display limit).</p>
    ) : null;
  }
  const none = meta.data.status === "none";
  return (
    <div
      role="status"
      className={`rounded-[var(--radius-panel)] border px-4 py-3 text-sm ${
        none ? "border-border bg-surface text-text-secondary" : "border-warn/40 bg-warn/10 text-warn"
      }`}
    >
      {none ? (
        <>
          <p className="font-medium text-text-primary">{meta.data.message}</p>
          <p className="mt-1 text-text-muted">Scores, trends and recommendations appear here once you have completed sessions.</p>
        </>
      ) : (
        <>
          <p className="font-medium">Early data</p>
          <p>More practice is needed for reliable trends ({meta.data.sessions} completed sessions so far).</p>
        </>
      )}
    </div>
  );
}
