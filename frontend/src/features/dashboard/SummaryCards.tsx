import { ArrowRight, BrainCircuit, MessageCircle, Shield, UserRound, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { ErrorState } from "@/components/ui/empty-state";
import { ProgressBar } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { percent, totalCompleted, totalStarted } from "@/features/dashboard/dashboardUtils";
import type { Resource } from "@/features/dashboard/useAsyncResource";
import { reveal } from "@/lib/motion";
import type { ProgressOverview } from "@/types/progress";

interface CardSpec {
  title: string;
  unit: string;
  to: string;
  icon: LucideIcon;
  iconBg: string;
  bar: string;
  pick: (o: ProgressOverview) => { done: number; total: number };
}

const BLUE = "linear-gradient(90deg,#2f6bff,#22b8ff)";
const CARDS: CardSpec[] = [
  { title: "Cybersecurity Learning", unit: "sessions completed", to: "/cybersecurity", icon: Shield, iconBg: "from-[#2f6bff] to-[#1d4ed8]", bar: BLUE, pick: (o) => ({ done: o.session_counts.practice_sessions.completed, total: o.session_counts.practice_sessions.total }) },
  { title: "Interview Preparation", unit: "sessions completed", to: "/interview", icon: UserRound, iconBg: "from-[#4f46e5] to-[#3730a3]", bar: BLUE, pick: (o) => ({ done: o.session_counts.interview_sessions.completed, total: o.session_counts.interview_sessions.total }) },
  { title: "Communication Practice", unit: "sessions completed", to: "/communication", icon: MessageCircle, iconBg: "from-[#2f6bff] to-[#2563eb]", bar: BLUE, pick: (o) => ({ done: o.session_counts.communication_sessions.completed, total: o.session_counts.communication_sessions.total }) },
  {
    title: "Overall Progress", unit: "activities", to: "/progress", icon: BrainCircuit, iconBg: "from-[#8b5cf6] to-[#6d28d9]", bar: "linear-gradient(90deg,#8b5cf6,#a78bfa)",
    pick: (o) => ({ done: totalCompleted(o.session_counts), total: totalStarted(o.session_counts) }),
  },
];

export function SummaryCards({ overview, onRetry }: { overview: Resource<ProgressOverview>; onRetry: () => void }) {
  if (overview.status === "error") {
    return (
      <div className="rounded-[var(--radius-card)] border border-border bg-surface p-5">
        <ErrorState message={overview.message} onRetry={onRetry} />
      </div>
    );
  }
  return (
    <section aria-label="Learning summary" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {CARDS.map((c, i) => {
        const r = reveal(i + 2);
        const Icon = c.icon;
        const v = overview.status === "ready" ? c.pick(overview.data) : null;
        const pct = v ? percent(v.done, v.total) : 0;
        return (
          <Link
            key={c.title}
            to={c.to}
            className={`${r.className} group block rounded-[var(--radius-card)] border border-border bg-surface p-4 shadow-card transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:border-signal/50 hover:shadow-pop`}
            style={r.style}
          >
            <div className="flex items-start justify-between">
              <span className={`flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-[0_8px_18px_-8px_rgb(47_107_255/0.8)] ${c.iconBg}`}>
                <Icon size={22} aria-hidden="true" />
              </span>
              <ArrowRight size={18} className="text-text-muted transition-transform duration-200 group-hover:translate-x-1 group-hover:text-text-primary" aria-hidden="true" />
            </div>
            <h2 className="mt-3.5 text-[13px] font-semibold leading-snug text-text-primary">{c.title}</h2>
            {v ? (
              <>
                <p className="mt-1 text-xs text-text-secondary">
                  {v.total > 0 ? (
                    <>
                      <span className="font-medium text-text-primary">{v.done}/{v.total}</span> {c.unit}
                    </>
                  ) : (
                    "No sessions yet"
                  )}
                </p>
                <div className="mt-3 flex items-center gap-3">
                  <ProgressBar value={pct} label={`${c.title}: ${pct}% complete`} color={c.bar} className="h-1.5 flex-1" />
                  <span className="w-9 text-right text-xs tabular-nums text-text-secondary">{v.total > 0 ? `${pct}%` : "—"}</span>
                </div>
              </>
            ) : (
              <div role="status" aria-label={`Loading ${c.title}`} className="mt-3 space-y-2.5">
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-1.5 w-full" />
              </div>
            )}
          </Link>
        );
      })}
    </section>
  );
}
