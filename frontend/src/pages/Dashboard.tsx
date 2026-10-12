import type { CSSProperties } from "react";
import { Bot, Flag, Gauge, History as HistoryIcon, ListChecks, MessagesSquare, Mic, ShieldHalf, Sparkles, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { DailyPracticeCard } from "@/components/dashboard/DailyPracticeCard";
import { buttonVariants } from "@/components/ui/button-variants";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { Badge } from "@/components/ui/badge";
import { firstName, formatScore, greetingFor, plural, totalCompleted, totalStarted } from "@/features/dashboard/dashboardUtils";
import { OverallTrendChart } from "@/features/dashboard/OverallTrendChart";
import { useAsyncResource } from "@/features/dashboard/useAsyncResource";
import { LearningFocusCard } from "@/features/personalization/LearningFocusCard";
import { TYPE_ACTION_LABEL, TYPE_ROUTE } from "@/features/progress/recommendationRoutes";
import { cn } from "@/lib/utils";
import * as progressService from "@/services/progressService";
import { useAuthStore } from "@/store/authStore";
import type { ActivityItem, Priority, ProgressOverview } from "@/types/progress";

const ACTIVITY_ICON: Record<ActivityItem["type"], typeof ShieldHalf> = {
  practice: ShieldHalf,
  ctf: Flag,
  communication: MessagesSquare,
  interview: Mic,
  pressure: Gauge,
};

const PRIORITY_TONE: Record<Priority, "danger" | "warn" | "neutral"> = { high: "danger", medium: "warn", low: "neutral" };

const QUICK_LINKS = [
  { label: "Talk to your AI Mentor", to: "/mentor", icon: Bot },
  { label: "Start a cybersecurity lab", to: "/cybersecurity", icon: ShieldHalf },
  { label: "Practice an interview", to: "/interview", icon: Mic },
];

/** Staggered entrance for the four top-level blocks: the one orchestrated moment on this page. */
const enter = (i: number): { className: string; style: CSSProperties } => ({
  className: "animate-rise-in",
  style: { animationDelay: `${i * 70}ms` },
});

function scoreHint(avg: number | null | undefined, empty: string): string {
  const s = formatScore(avg);
  return s ? `Average score ${s}` : empty;
}

function Stats({ overview, onRetry }: { overview: ReturnType<typeof useAsyncResource<ProgressOverview>>[0]; onRetry: () => void }) {
  if (overview.status === "error") {
    return (
      <Card>
        <CardContent className="py-5">
          <ErrorState message={overview.message} onRetry={onRetry} />
        </CardContent>
      </Card>
    );
  }
  const loading = overview.status === "loading";
  const d = overview.status === "ready" ? overview.data : null;
  const c = d?.session_counts;
  return (
    <section aria-label="Learning statistics" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        loading={loading}
        icon={ShieldHalf}
        label="Cybersecurity practice"
        value={c ? c.practice_sessions.completed : "—"}
        hint={
          d
            ? `${plural(d.cybersecurity_performance.categories_practiced, "topic area")} · ${scoreHint(d.cybersecurity_performance.average_score, "no score yet")}`
            : undefined
        }
      />
      <StatCard
        loading={loading}
        icon={Mic}
        label="Interview preparation"
        value={c ? c.interview_sessions.completed : "—"}
        hint={d ? scoreHint(d.interview_performance?.overall_score, "No interviews scored yet") : undefined}
      />
      <StatCard
        loading={loading}
        icon={MessagesSquare}
        label="Communication practice"
        value={c ? c.communication_sessions.completed : "—"}
        hint={d ? scoreHint(d.communication_performance?.overall_score, "No conversations scored yet") : undefined}
      />
      <StatCard
        loading={loading}
        icon={TrendingUp}
        label="Sessions completed"
        value={c ? totalCompleted(c) : "—"}
        hint={c ? `of ${totalStarted(c)} started across all modes` : undefined}
      />
    </section>
  );
}

export default function Dashboard() {
  const name = useAuthStore((s) => s.user?.name);
  const [overview, reloadOverview] = useAsyncResource(progressService.getOverview, "Couldn't load your progress.");
  const [trends, reloadTrends] = useAsyncResource(() => progressService.getTrends("30d"), "Couldn't load your trend.");

  const hasActivity = overview.status === "ready" && overview.data.has_activity;
  const e0 = enter(0), e1 = enter(1), e2 = enter(2), e3 = enter(3);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className={cn("grid grid-cols-1 gap-4 lg:grid-cols-3", e0.className)} style={e0.style}>
        <section className="glass relative overflow-hidden rounded-[var(--radius-card)] border border-border-strong/70 px-6 py-7 shadow-card md:px-8 md:py-9 lg:col-span-2">
          <div aria-hidden="true" className="bg-grid pointer-events-none absolute inset-0" />
          <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-violet/15 blur-3xl" />
          <div className="relative flex h-full flex-col">
            <h1 className="font-display text-2xl font-semibold text-text-primary md:text-3xl">
              {greetingFor(new Date().getHours())}, {firstName(name)}
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-text-secondary">
              {overview.status === "ready"
                ? hasActivity
                  ? `You've completed ${plural(totalCompleted(overview.data.session_counts), "session")} so far. Pick up where your plan says to next.`
                  : "Complete your first practice session and this page will start tracking your skills, trends and next steps."
                : "Your learning progress, practice plan and next steps in one place."}
            </p>
            <div className="mt-auto flex flex-wrap gap-2 pt-6">
              {QUICK_LINKS.map(({ label, to, icon: Icon }, i) => (
                <Link key={to} to={to} className={buttonVariants({ variant: i === 0 ? "primary" : "secondary", size: "md" })}>
                  <Icon size={15} aria-hidden="true" />
                  {label}
                </Link>
              ))}
            </div>
          </div>
        </section>
        <DailyPracticeCard />
      </div>

      <div className={e1.className} style={e1.style}>
        <Stats overview={overview} onRetry={reloadOverview} />
      </div>

      <section className={cn("grid grid-cols-1 gap-4 lg:grid-cols-3", e2.className)} style={e2.style}>
        <Card className="lg:col-span-2">
          <CardHeader className="flex items-center justify-between gap-3">
            <CardTitle>Overall progress, last 30 days</CardTitle>
            {trends.status === "ready" && trends.data.dimensions.overall.trend !== "insufficient_data" && (
              <Badge tone={trends.data.dimensions.overall.trend === "improving" ? "success" : trends.data.dimensions.overall.trend === "declining" ? "danger" : "neutral"}>
                {trends.data.dimensions.overall.trend === "improving" ? "Improving" : trends.data.dimensions.overall.trend === "declining" ? "Declining" : "Stable"}
              </Badge>
            )}
          </CardHeader>
          <CardContent>
            {trends.status === "loading" && (
              <div role="status" aria-label="Loading trend">
                <Skeleton className="h-52 w-full rounded-[var(--radius-panel)]" />
              </div>
            )}
            {trends.status === "error" && <ErrorState message={trends.message} onRetry={reloadTrends} />}
            {trends.status === "ready" &&
              (trends.data.dimensions.overall.trend === "insufficient_data" || trends.data.dimensions.overall.points.length < 2 ? (
                <EmptyState
                  icon={TrendingUp}
                  title="Not enough data for a trend yet"
                  description="Complete a few more sessions and your overall score over time will appear here."
                  action={
                    <Link to="/cybersecurity" className={buttonVariants({ variant: "secondary", size: "sm" })}>
                      Start practicing
                    </Link>
                  }
                />
              ) : (
                <OverallTrendChart series={trends.data.dimensions.overall} />
              ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ListChecks size={15} className="text-signal" aria-hidden="true" /> Recommended next
            </CardTitle>
          </CardHeader>
          <CardContent>
            {overview.status === "loading" && (
              <div role="status" aria-label="Loading recommendations" className="space-y-3">
                <Skeleton className="h-14 w-full rounded-[var(--radius-panel)]" />
                <Skeleton className="h-14 w-full rounded-[var(--radius-panel)]" />
              </div>
            )}
            {overview.status === "error" && <ErrorState message={overview.message} onRetry={reloadOverview} />}
            {overview.status === "ready" &&
              (overview.data.recommendations.length === 0 ? (
                <EmptyState
                  icon={Sparkles}
                  title="No recommendations yet"
                  description="After a few sessions we'll suggest what to focus on, based on your actual results."
                />
              ) : (
                <ul className="space-y-2">
                  {overview.data.recommendations.slice(0, 3).map((rec) => (
                    <li key={rec._id}>
                      <Link
                        to={TYPE_ROUTE[rec.type]}
                        className="group block rounded-[var(--radius-panel)] border border-border bg-surface-raised/40 px-3 py-2.5 transition-colors hover:border-border-input hover:bg-surface-raised"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium text-text-primary">{rec.area}</p>
                          <Badge tone={PRIORITY_TONE[rec.priority]}>{rec.priority}</Badge>
                        </div>
                        <p className="mt-0.5 line-clamp-2 text-xs text-text-secondary">{rec.reason}</p>
                        <p className="mt-1.5 text-xs font-medium text-signal">{TYPE_ACTION_LABEL[rec.type]}</p>
                      </Link>
                    </li>
                  ))}
                </ul>
              ))}
          </CardContent>
        </Card>
      </section>

      <section className={cn("grid grid-cols-1 gap-4 lg:grid-cols-2", e3.className)} style={e3.style}>
        <LearningFocusCard />
        <Card>
          <CardHeader className="flex items-center justify-between gap-3">
            <CardTitle className="flex items-center gap-2">
              <HistoryIcon size={15} className="text-signal" aria-hidden="true" /> Recent activity
            </CardTitle>
            <Link to="/history" className="text-xs text-signal hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardContent>
            {overview.status === "loading" && (
              <div role="status" aria-label="Loading recent activity" className="space-y-3">
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} className="h-10 w-full rounded-[var(--radius-panel)]" />
                ))}
              </div>
            )}
            {overview.status === "error" && (
              <ErrorState message={overview.message} onRetry={reloadOverview} />
            )}
            {overview.status === "ready" &&
              (overview.data.recent_activity.length === 0 ? (
                <EmptyState
                  icon={HistoryIcon}
                  title="No activity yet"
                  description="Finish a session and it will show up here."
                  action={
                    <Link to="/practice" className={buttonVariants({ variant: "secondary", size: "sm" })}>
                      Start a session
                    </Link>
                  }
                />
              ) : (
                <ul className="divide-y divide-border">
                  {overview.data.recent_activity.slice(0, 5).map((item, i) => {
                    const Icon = ACTIVITY_ICON[item.type];
                    return (
                      <li key={`${item.type}-${item.completed_at}-${i}`} className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-panel)] bg-surface-raised text-text-secondary">
                          <Icon size={15} aria-hidden="true" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm text-text-primary">{item.label}</span>
                          <span className="block text-xs text-text-muted">{new Date(item.completed_at).toLocaleDateString()}</span>
                        </span>
                        {formatScore(item.score) && <span className="shrink-0 text-sm font-medium tabular-nums text-text-secondary">{formatScore(item.score)}</span>}
                      </li>
                    );
                  })}
                </ul>
              ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
