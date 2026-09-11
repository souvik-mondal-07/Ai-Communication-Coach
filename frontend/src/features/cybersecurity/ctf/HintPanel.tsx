import { Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { HINT_LEVELS, type CtfHint, type HintLevel } from "@/features/cybersecurity/ctf/ctfTypes";

interface HintPanelProps {
  hints: CtfHint[];
  onRequestHint: (level: HintLevel) => void;
  isRequesting: boolean;
}

const HINT_ORDER: HintLevel[] = ["hint_1", "hint_2", "hint_3"];

export function HintPanel({ hints, onRequestHint, isRequesting }: HintPanelProps) {
  const obtainedLevels = new Set(hints.map((h) => h.level));

  function isLocked(level: HintLevel): boolean {
    // Solution can always be requested directly; hint_1/2/3 unlock in order.
    if (level === "solution") return false;
    const index = HINT_ORDER.indexOf(level);
    if (index === 0) return false;
    return !obtainedLevels.has(HINT_ORDER[index - 1]);
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {HINT_LEVELS.map(({ level, label }) => {
          const obtained = obtainedLevels.has(level);
          const locked = !obtained && isLocked(level);
          return (
            <Button
              key={level}
              type="button"
              variant={obtained ? "secondary" : "primary"}
              size="sm"
              disabled={locked || isRequesting}
              onClick={() => onRequestHint(level)}
              className="gap-1.5"
            >
              {locked && <Lock size={12} />}
              {label}
              {obtained && " ✓"}
            </Button>
          );
        })}
      </div>

      {hints.length > 0 && (
        <div className="space-y-2">
          {HINT_LEVELS.filter(({ level }) => obtainedLevels.has(level)).map(({ level, label }) => {
            const hint = hints.find((h) => h.level === level);
            if (!hint) return null;
            return (
              <div
                key={level}
                className="rounded-[var(--radius-panel)] border border-border bg-surface-raised p-3"
              >
                <p className="mb-1 text-xs font-medium text-signal">{label}</p>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">
                  {hint.content}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
