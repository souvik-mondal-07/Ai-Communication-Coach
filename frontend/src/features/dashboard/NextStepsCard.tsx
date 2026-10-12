import { ArrowRight, Flag, Lightbulb, MessageCircle, Shield, UserRound, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { Resource } from "@/features/dashboard/useAsyncResource";
import { reveal } from "@/lib/motion";
import { buildSteps } from "@/features/dashboard/nextSteps";
import type { Priority, ProgressOverview, RecommendationType } from "@/types/progress";

const ICON: Record<RecommendationType, { icon: LucideIcon; bg: string }> = {
  practice: { icon: Shield, bg: "from-[#2f6bff] to-[#1d4ed8]" },
  interview: { icon: UserRound, bg: "from-[#4f46e5] to-[#3730a3]" },
  communication: { icon: MessageCircle, bg: "from-[#10b981] to-[#047857]" },
  ctf: { icon: Flag, bg: "from-[#8b5cf6] to-[#6d28d9]" },
  pressure: { icon: Shield, bg: "from-[#f59e0b] to-[#b45309]" },
};

const PRIORITY_LABEL: Record<Priority, string> = { high: "High priority", medium: "Medium priority", low: "Low priority" };

export function NextStepsCard({ overview, onRetry }: { overview: Resource<ProgressOverview>; onRetry: () => void }) {
  const r = reveal(6);
  const { steps, personalised } = buildSteps(overview.status === "ready" ? overview.data : null);
  return (
    <section aria-labelledby="next-steps-title" className={`${r.className} rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-card`} style={r.style}>
      <div className="flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#3a3217]/70 text-amber"><Lightbulb size={18} aria-hidden="true" /></span>
        <div>
          <h2 id="next-steps-title" className="font-display text-[15px] font-semibold text-text-primary">Recommended Next Steps</h2>
          {overview.status === "ready" && (
            <p className="text-xs text-text-muted">{personalised ? "Includes suggestions based on your results" : "General suggestions — finish a few sessions to personalise these"}</p>
          )}
        </div>
      </div>

      {overview.status === "error" ? (
        <div className="mt-4"><ErrorState message={overview.message} onRetry={onRetry} /></div>
      ) : overview.status === "loading" ? (
        <div role="status" aria-label="Loading recommendations" className="mt-3.5 space-y-2">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[62px] w-full rounded-[var(--radius-panel)]" />)}
        </div>
      ) : (
        <ul className="mt-3.5 space-y-2">
          {steps.map((s) => {
            const { icon: Icon, bg } = ICON[s.type];
            return (
              <li key={s.key}>
                <Link to={s.to} className="group flex items-center gap-3 rounded-[var(--radius-panel)] border border-border bg-surface-raised/40 p-2.5 transition-[border-color,background-color,transform] duration-200 hover:translate-x-0.5 hover:border-signal/50 hover:bg-surface-raised">
                  <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br text-white ${bg}`}><Icon size={20} aria-hidden="true" /></span>
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                      <span className="text-[13px] font-medium text-text-primary">{s.title}</span>
                      {s.priority && <span className="shrink-0 rounded-full border border-border-strong px-2 py-px text-[10px] text-text-secondary">{PRIORITY_LABEL[s.priority]}</span>}
                    </span>
                    <span className="mt-0.5 line-clamp-2 block text-[11.5px] leading-snug text-text-secondary">{s.description}</span>
                  </span>
                  <ArrowRight size={16} className="shrink-0 text-text-muted transition-transform duration-200 group-hover:translate-x-1" aria-hidden="true" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
