import { useEffect } from "react";
import { CalendarCheck } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { goalPercent } from "@/components/dashboard/dailyPracticeUtils";
import { StreakBadge } from "@/components/dashboard/StreakCard";
import { Card, CardContent } from "@/components/ui/card";
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
          <p className="text-sm text-text-muted" aria-label="Loading today's practice">
            Loading today's practice…
          </p>
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
            <div>
              <div className="flex items-baseline justify-between text-xs text-text-secondary">
                <span>{data.goal.goal_minutes} min goal</span>
                <span>
                  Progress: {data.goal.minutes_done} / {data.goal.goal_minutes} min
                </span>
              </div>
              <div
                className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-raised"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={goalPercent(data.goal.minutes_done, data.goal.goal_minutes)}
                aria-label="Daily practice progress"
              >
                <div
                  className="h-full bg-signal"
                  style={{ width: `${goalPercent(data.goal.minutes_done, data.goal.goal_minutes)}%` }}
                />
              </div>
              <p className="mt-1 text-[11px] text-text-muted">
                {data.goal.tasks_done} of {data.goal.tasks_total} tasks done
              </p>
            </div>

            <div>
              <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">Recommended</p>
              <p className="mt-0.5 text-sm text-text-primary">{data.plan.focus.title}</p>
            </div>

            {data.plan.status === "completed" ? (
              <Link
                to="/daily-practice"
                className="inline-flex rounded-[var(--radius-panel)] border border-border px-3 py-1.5 text-xs font-medium text-text-primary hover:border-border-strong"
              >
                View today's summary
              </Link>
            ) : (
              <button
                type="button"
                onClick={onStart}
                disabled={isActing}
                className="inline-flex rounded-[var(--radius-panel)] bg-signal px-3 py-1.5 text-xs font-medium text-[#08120f] hover:opacity-90 disabled:opacity-60"
              >
                {isActing ? "Starting…" : data.plan.status === "in_progress" ? "Continue Practice" : "Start Practice"}
              </button>
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
