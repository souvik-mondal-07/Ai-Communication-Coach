import type { CurrentPressurePrompt } from "@/types/pressure";

interface PressureQuestionProps {
  prompt: CurrentPressurePrompt;
}

const FOLLOW_UP_LABELS = {
  rapid: "Rapid Follow-up",
  interruption: "Interruption",
  technical: "Follow-up",
} as const;

/** The single prompt currently being asked — a main question, a rapid follow-up, or an interruption. */
export function PressureQuestion({ prompt }: PressureQuestionProps) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
        {!prompt.is_follow_up && <span>{prompt.topic_label}</span>}
        {prompt.is_follow_up && prompt.follow_up_kind && (
          <span
            className={
              prompt.follow_up_kind === "interruption"
                ? "rounded-full border border-warn/40 bg-warn/10 px-2 py-0.5 text-warn"
                : "rounded-full border border-signal/40 bg-signal/10 px-2 py-0.5 text-signal"
            }
          >
            {FOLLOW_UP_LABELS[prompt.follow_up_kind]}
          </span>
        )}
      </div>
      <p className="font-display text-lg leading-snug text-text-primary" data-testid="pressure-question">
        “{prompt.question}”
      </p>
    </div>
  );
}
