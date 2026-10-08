import { Check, Circle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DailyTask } from "@/types/dailyPractice";

const KIND_LABEL = { cybersecurity: "Cybersecurity", communication: "Communication", interview: "Interview" } as const;

export function taskActionLabel(task: DailyTask): string {
  if (task.status === "completed") return "Done";
  return task.status === "in_progress" ? "Continue" : "Start";
}

interface Props {
  tasks: DailyTask[];
  busy: boolean;
  onOpen: (task: DailyTask) => void;
}

/** The daily checklist. Each task opens in the module that owns that kind of practice. */
export function DailyTaskList({ tasks, busy, onOpen }: Props) {
  return (
    <ul className="space-y-3">
      {tasks.map((task) => (
        <li key={task.task_id} className="rounded-[var(--radius-panel)] border border-border bg-surface p-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5" aria-hidden="true">
              {task.status === "completed" ? (
                <Check size={18} className="text-signal" />
              ) : task.status === "in_progress" ? (
                <Loader2 size={18} className="text-warn" />
              ) : (
                <Circle size={18} className="text-text-muted" />
              )}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[11px] text-text-muted">
                {KIND_LABEL[task.kind]} · ~{task.est_minutes} min
                {task.status === "completed" && task.score !== null && ` · Score ${task.score}`}
              </p>
              <p className={cn("text-sm font-medium", task.status === "completed" ? "text-text-secondary" : "text-text-primary")}>
                {task.title}
              </p>
              <p className="mt-0.5 text-xs text-text-secondary">{task.description}</p>
              {task.why.length > 0 && task.status !== "completed" && (
                <ul className="mt-2 list-disc space-y-0.5 pl-4 text-[11px] text-text-muted">
                  {task.why.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              )}
            </div>
            {task.status !== "completed" && (
              <button
                type="button"
                disabled={busy}
                onClick={() => onOpen(task)}
                className="shrink-0 rounded-[var(--radius-panel)] bg-signal px-3 py-1.5 text-xs font-medium text-[#08120f] hover:opacity-90 disabled:opacity-60"
              >
                {taskActionLabel(task)}
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
