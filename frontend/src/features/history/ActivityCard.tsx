import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/utils/formatters";
import type { HistoryActivity } from "@/types/history";
import { formatElapsed, STATUS_LABELS, TYPE_META } from "@/features/history/historyMeta";

const STATUS_STYLE: Record<HistoryActivity["status"], string> = {
  completed: "text-signal",
  in_progress: "text-warn",
  abandoned: "text-text-muted",
};

export function ActivityCard({ activity }: { activity: HistoryActivity }) {
  const { icon: Icon } = TYPE_META[activity.type];
  const facts = [
    formatDateTime(activity.created_at),
    activity.duration_seconds != null ? formatElapsed(activity.duration_seconds) : null,
  ].filter(Boolean);

  return (
    <Link
      to={`/history/${activity.type}/${activity.id}`}
      className="group flex items-center gap-3 rounded-[var(--radius-panel)] border border-border bg-surface p-4 transition-colors hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius-panel)] bg-signal/10 text-signal">
        <Icon size={18} aria-hidden="true" />
      </div>

      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">{activity.type_label}</p>
        <p className="truncate text-sm font-semibold text-text-primary">{activity.title}</p>
        {activity.description && <p className="truncate text-xs text-text-secondary">{activity.description}</p>}
        <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-text-muted">
          <span>{facts.join(" · ")}</span>
          {activity.score != null && <span className="font-medium text-text-secondary">Score: {activity.score}</span>}
          <span className={cn("font-medium", STATUS_STYLE[activity.status])}>{STATUS_LABELS[activity.status]}</span>
        </p>
      </div>

      <span className="flex shrink-0 items-center gap-1 text-xs text-text-secondary group-hover:text-text-primary">
        <span className="hidden sm:inline">View</span>
        <ChevronRight size={16} aria-hidden="true" />
      </span>
    </Link>
  );
}
