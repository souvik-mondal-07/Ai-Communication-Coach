import { useEffect } from "react";
import { ArrowRight, CalendarCheck, Check } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { buttonVariants } from "@/components/ui/button-variants";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { LaptopArt } from "@/features/dashboard/DashboardArt";
import { reveal } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useDailyPracticeStore } from "@/store/dailyPracticeStore";
import type { TaskKind } from "@/types/dailyPractice";

const KIND_LABEL: Record<TaskKind, string> = {
  cybersecurity: "Cybersecurity Learning",
  interview: "Interview Preparation",
  communication: "Communication Practice",
};

/**
 * Today's plan from the daily-practice API. Completion is read-only here: a task
 * becomes done when its linked session finishes (server-side), not from a checkbox.
 */
export function TodayPracticeCard() {
  const navigate = useNavigate();
  const { data, isLoading, error, isActing, actionError, load, start } = useDailyPracticeStore();
  const r = reveal(7);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleStart() {
    const route = await start();
    if (route) navigate(route);
  }

  const plan = data?.plan ?? null;
  const done = plan?.status === "completed";

  return (
    <section aria-labelledby="today-title" className={`${r.className} flex flex-col rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-card`} style={r.style}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#1d2a6b]/80 text-[#8fa6ff]"><CalendarCheck size={18} aria-hidden="true" /></span>
          <h2 id="today-title" className="font-display text-[15px] font-semibold text-text-primary">Today&apos;s Practice</h2>
        </div>
        <Link to="/daily-practice" className="rounded text-xs text-link transition-colors hover:text-text-primary hover:underline">View All</Link>
      </div>

      {isLoading && !data && (
        <div role="status" aria-label="Loading today's practice" className="mt-4 space-y-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-10 w-full rounded-[var(--radius-panel)]" />)}
        </div>
      )}
      {error && !data && (
        <p role="alert" className="mt-4 text-sm text-danger">
          {error}{" "}
          <button type="button" onClick={() => void load()} className="underline">Retry</button>
        </p>
      )}
      {data && !data.enabled && (
        <p className="mt-4 text-sm text-text-secondary">
          Daily practice is turned off. <Link to="/settings" className="text-link hover:underline">Turn it on in Settings</Link>.
        </p>
      )}
      {data && data.enabled && !plan && (
        <p className="mt-4 text-sm text-text-secondary">{data.rest_day ? "Today is a rest day in your schedule. Practice any time if you like." : "No practice planned today."}</p>
      )}

      {plan && (
        <div className="mt-4 flex flex-1 flex-col gap-4 sm:flex-row sm:items-stretch">
          <ul className="min-w-0 flex-1 space-y-3">
            {plan.tasks.map((t) => {
              const complete = t.status === "completed";
              return (
                <li key={t.task_id} className="flex items-start gap-3.5">
                  <span
                    className={cn("mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2", complete ? "border-success bg-success text-[#04271a]" : "border-border-input text-transparent")}
                    role="img"
                    aria-label={complete ? "Completed" : t.status === "in_progress" ? "In progress" : "Not started"}
                  >
                    {complete && <Check size={14} strokeWidth={3} className="animate-check-pop" aria-hidden="true" />}
                  </span>
                  <span className="min-w-0">
                    <span className={"block text-[13px] font-medium text-text-primary"}>{t.title}</span>
                    <span className="block text-xs text-text-muted">
                      {KIND_LABEL[t.kind]} · {t.est_minutes} min
                    </span>
                  </span>
                </li>
              );
            })}
          </ul>
          <div className="flex shrink-0 flex-col items-center justify-end gap-3 sm:w-48">
            <LaptopArt className="animate-float-slow hidden h-24 w-auto sm:block" />
            {done ? (
              <Link to="/daily-practice" className={cn(buttonVariants({ size: "md" }), "h-11 w-full")}>View summary <ArrowRight size={16} aria-hidden="true" /></Link>
            ) : (
              <Button size="md" className="h-11 w-full" onClick={() => void handleStart()} loading={isActing}>
                {isActing ? "Starting…" : "Continue Learning"} {!isActing && <ArrowRight size={16} aria-hidden="true" />}
              </Button>
            )}
          </div>
        </div>
      )}
      {actionError && <p role="alert" className="mt-3 text-xs text-danger">{actionError}</p>}
    </section>
  );
}
