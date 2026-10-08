import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { StreakCard } from "@/components/dashboard/StreakCard";
import { goalPercent } from "@/components/dashboard/dailyPracticeUtils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DailySummaryCard } from "@/features/dailyPractice/DailySummaryCard";
import { DailyTaskList } from "@/features/dailyPractice/DailyTaskList";
import { useDailyPracticeStore } from "@/store/dailyPracticeStore";
import type { DailyTask } from "@/types/dailyPractice";

/**
 * Today's practice. This page only orchestrates: each task is started through the existing
 * cybersecurity / communication / interview flow and linked back here.
 */
export default function DailyPractice() {
  const navigate = useNavigate();
  const { data, isLoading, isActing, error, actionError, load, openTask, regenerate, complete } = useDailyPracticeStore();

  // Refetch whenever the page is shown (e.g. returning from a finished session).
  useEffect(() => {
    void load();
  }, [load]);

  async function handleOpen(task: DailyTask) {
    try {
      navigate(await openTask(task));
    } catch {
      /* error text is in the store */
    }
  }

  if (isLoading && !data) return <p className="text-sm text-text-muted">Loading today's practice…</p>;
  if (error && !data) {
    return (
      <div role="alert" className="text-sm text-danger">
        {error}{" "}
        <button type="button" onClick={() => void load()} className="underline">
          Retry
        </button>
      </div>
    );
  }
  if (!data) return null;

  const plan = data.plan;
  const untouched = plan?.status === "pending" && plan.tasks.every((t) => t.status === "pending");
  const anyDone = plan?.tasks.some((t) => t.status === "completed") ?? false;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="font-display text-xl font-semibold text-text-primary">Today's Practice</h2>
        <p className="mt-1 text-sm text-text-secondary">{data.date} · your personalized daily routine</p>
      </div>

      {!data.enabled && (
        <Card>
          <CardContent className="py-5 text-sm text-text-secondary">
            Daily practice is turned off. <Link to="/settings" className="text-signal hover:underline">Turn it on in Settings</Link>.
          </CardContent>
        </Card>
      )}

      {data.enabled && !plan && (
        <Card>
          <CardContent className="py-5 text-sm text-text-secondary">
            {data.rest_day ? "Today is a rest day in your schedule. You can still practice from any page." : "No practice planned today."}
          </CardContent>
        </Card>
      )}

      {plan && data.goal && (
        <>
          <Card>
            <CardContent className="space-y-3 py-5">
              <div className="flex items-baseline justify-between text-sm">
                <span className="text-text-secondary">
                  Goal: {data.goal.goal_minutes} min · {plan.difficulty} difficulty
                </span>
                <span className="text-text-primary">
                  {data.goal.minutes_done} / {data.goal.goal_minutes} min
                </span>
              </div>
              <div
                className="h-2 overflow-hidden rounded-full bg-surface-raised"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={goalPercent(data.goal.minutes_done, data.goal.goal_minutes)}
                aria-label="Daily practice progress"
              >
                <div className="h-full bg-signal" style={{ width: `${goalPercent(data.goal.minutes_done, data.goal.goal_minutes)}%` }} />
              </div>
              <p className="text-xs text-text-muted">
                {data.goal.tasks_done} of {data.goal.tasks_total} tasks done. Minutes count any practice you finish today.
              </p>
            </CardContent>
          </Card>

          {plan.status === "completed" && plan.summary && (
            <DailySummaryCard summary={plan.summary} partial={plan.completion === "partial"} />
          )}

          <DailyTaskList tasks={plan.tasks} busy={isActing || plan.status === "completed"} onOpen={(t) => void handleOpen(t)} />

          {actionError && (
            <p role="alert" className="text-sm text-danger">
              {actionError}
            </p>
          )}

          {plan.status !== "completed" && (
            <div className="flex flex-wrap gap-2">
              {anyDone && (
                <Button variant="secondary" disabled={isActing} onClick={() => void complete()}>
                  Finish for today
                </Button>
              )}
              {untouched && (
                <Button variant="ghost" disabled={isActing} onClick={() => void regenerate()}>
                  Get a different practice
                </Button>
              )}
            </div>
          )}
        </>
      )}

      <StreakCard streak={data.streak} />
    </div>
  );
}
