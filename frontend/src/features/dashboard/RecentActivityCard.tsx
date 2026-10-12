import { Flag, Gauge, History as HistoryIcon, MessageCircle, Mic, Shield, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { buttonVariants } from "@/components/ui/button-variants";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatScore, relativeTime } from "@/features/dashboard/dashboardUtils";
import type { Resource } from "@/features/dashboard/useAsyncResource";
import { reveal } from "@/lib/motion";
import type { ActivityItem, ProgressOverview } from "@/types/progress";

const META: Record<ActivityItem["type"], { icon: LucideIcon; feature: string; tone: string }> = {
  practice: { icon: Shield, feature: "Cybersecurity Learning", tone: "bg-[#0f3f3d] text-[#34d3b4]" },
  interview: { icon: Mic, feature: "Interview Simulator", tone: "bg-[#1b2a73] text-[#8fa6ff]" },
  communication: { icon: MessageCircle, feature: "Communication Practice", tone: "bg-[#0f3a3a] text-[#34d3b4]" },
  ctf: { icon: Flag, feature: "CTF & Labs", tone: "bg-[#33225f] text-[#b79bff]" },
  pressure: { icon: Gauge, feature: "Pressure Training", tone: "bg-[#4a3512] text-[#f5b042]" },
};

export function RecentActivityCard({ overview, onRetry }: { overview: Resource<ProgressOverview>; onRetry: () => void }) {
  const r = reveal(3);
  return (
    <section aria-labelledby="activity-title" className={`${r.className} rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-card`} style={r.style}>
      <div className="flex items-center justify-between">
        <h2 id="activity-title" className="font-display text-[15px] font-semibold text-text-primary">Recent Activity</h2>
        <Link to="/history" className="rounded text-xs text-link transition-colors hover:text-text-primary hover:underline">View All</Link>
      </div>
      <div className="mt-4">
        {overview.status === "loading" && (
          <div role="status" aria-label="Loading recent activity" className="space-y-4">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full rounded-[var(--radius-panel)]" />)}
          </div>
        )}
        {overview.status === "error" && <ErrorState message={overview.message} onRetry={onRetry} />}
        {overview.status === "ready" &&
          (overview.data.recent_activity.length === 0 ? (
            <EmptyState
              icon={HistoryIcon}
              title="No activity yet"
              description="Finish a session and it will show up here."
              action={<Link to="/practice" className={buttonVariants({ variant: "secondary", size: "sm" })}>Start a session</Link>}
            />
          ) : (
            <ul className="space-y-3.5">
              {overview.data.recent_activity.slice(0, 4).map((item, i) => {
                const m = META[item.type];
                const Icon = m.icon;
                const score = formatScore(item.score);
                return (
                  <li key={`${item.type}-${item.completed_at}-${i}`} className="flex items-center gap-3.5">
                    <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${m.tone}`}><Icon size={20} aria-hidden="true" /></span>
                    <span className="min-w-0 flex-1">
                      <span className="line-clamp-2 block text-[13px] font-medium text-text-primary">{item.label}</span>
                      <span className="block truncate text-xs text-text-muted">{m.feature}</span>
                      <span className="block text-xs text-text-muted">{relativeTime(item.completed_at)}</span>
                    </span>
                    {score && <span className="shrink-0 text-xs font-medium tabular-nums text-text-secondary">{score}</span>}
                  </li>
                );
              })}
            </ul>
          ))}
      </div>
    </section>
  );
}
