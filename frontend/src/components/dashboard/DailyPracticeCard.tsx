import { useEffect } from "react";
import { CalendarCheck } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { goalPercent } from "@/components/dashboard/dailyPracticeUtils";
import { StreakBadge } from "@/components/dashboard/StreakCard";
import { Button } from "@/components/ui/button";
import { buttonVariants } from "@/components/ui/button-variants";
import { Card, CardContent } from "@/components/ui/card";
import { ProgressRing } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useDailyPracticeStore } from "@/store/dailyPracticeStore";
import type { DailyPracticeState } from "@/types/dailyPractice";

interface ViewProps {
  data: DailyPracticeState | null;
  isLoading: boolean;
  error: string | null;
  isActing?: boolean;
  actionError?: string | null;
  onStart: () => void;
  onRetry: () => void;
}

/** Presentational card: every number comes from the daily-practice API response. */
export function DailyPracticeCardView({ data, isLoading, error, isActing = false, actionError, onStart, onRetry }: ViewProps) {
  const pct = data?.goal ? goalPercent(data.goal.minutes_done, data.goal.goal_minutes) : 0;
  return (
    <Card>
      <CardContent className="space-y-4 py-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <CalendarCheck size={16} className="text-signal" aria-hidden="true" />
            <h3 className="text-sm font-semibold text-text-primary">Today's Practice</h3>
          </div>
          {data && <StreakBadge streak={data.streak} />}
        </div>

        {isLoading && !data && (
          <div role="status" className="flex items-center gap-4">
            <span className="sr-only">Loading today's practice…</span>
            <Skeleton className="h-24 w-24 shrink-0 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-8 w-28 rounded-[var(--radius-panel)]" />
            </div>
          </div>
        )}
        {error && !data && (
          <div role="alert" className="text-sm text-danger">
            {error}{" "}
            <button type="button" onClick={onRetry} className="underline">
              Retry
            </button>
          </div>
        )}

        {data && !data.enabled && (
          <p className="text-sm text-text-secondary">
            Daily practice is turned off.{" "}
            <Link to="/settings" className="text-signal hover:underline">
              Turn it on in Settings
            </Link>
            .
          </p>
        )}
        {data && data.enabled && !data.plan && (
          <p className="text-sm text-text-secondary">
            {data.rest_day ? "Today is a rest day in your schedule. Practice any time if you like." : "No practice planned today."}
          </p>
        )}

        {data?.plan && data.goal && (
          <>
            <div className="flex items-center gap-4">
              <ProgressRing value={pct} size={96} stroke={9} label="Daily practice progress">
                <span className="font-display text-xl font-semibold tabular-nums text-text-primary">{pct}%</span>
              </ProgressRing>
              <div className="min-w-0 flex-1 space-y-1">
                <p className="text-xs text-text-secondary">{data.goal.goal_minutes} min goal</p>
                <p className="text-xs text-text-secondary">
                  Progress: {data.goal.minutes_done} / {data.goal.goal_minutes} min
                </p>
                <p className="text-[11px] text-text-muted">
                  {data.goal.tasks_done} of {data.goal.tasks_total} tasks done
                </p>
              </div>
            </div>

            <div>
              <p className="text-[11px] font-medium text-text-muted">Recommended</p>
              <p className="mt-0.5 text-sm text-text-primary">{data.plan.focus.title}</p>
            </div>

            {data.plan.status === "completed" ? (
              <Link to="/daily-practice" className={buttonVariants({ variant: "secondary", size: "sm" })}>
                View today's summary
              </Link>
            ) : (
              <Button size="sm" onClick={onStart} loading={isActing}>
                {isActing ? "Starting…" : data.plan.status === "in_progress" ? "Continue Practice" : "Start Practice"}
              </Button>
            )}
            {actionError && (
              <p role="alert" className="text-xs text-danger">
                {actionError}
              </p>
            )}
          </>
        )}

        {data && (
          <p className="border-t border-border pt-3 text-xs text-text-secondary">
            <Link to="/notifications" className="hover:text-text-primary">
              Unread notifications:{" "}
              <span className="font-medium text-text-primary">{data.unread_notifications}</span>
            </Link>
          </p>
        )}
      </CardContent>
    </Card>
  );
}

/** Dashboard card wired to the daily-practice store. */
export function DailyPracticeCard() {
  const navigate = useNavigate();
  const { data, isLoading, error, isActing, actionError, load, start } = useDailyPracticeStore();

  useEffect(() => {
    void load();
  }, [load]);

  async function handleStart() {
    const route = await start();
    if (route) navigate(route);
  }

  return (
    <DailyPracticeCardView
      data={data}
      isLoading={isLoading}
      error={error}
      isActing={isActing}
      actionError={actionError}
      onStart={() => void handleStart()}
      onRetry={() => void load()}
    />
  );
}
