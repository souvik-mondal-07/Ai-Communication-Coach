import { cn } from "@/lib/utils";
import type { PressureLevelInfo } from "@/types/pressure";

interface PressureLevelCardProps {
  level: PressureLevelInfo;
  selected: boolean;
  onSelect: () => void;
}

/** One selectable pressure level, showing what changes at that level — not the internal odds behind it. */
export function PressureLevelCard({ level, selected, onSelect }: PressureLevelCardProps) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cn(
        "w-full rounded-[var(--radius-panel)] border px-4 py-3 text-left transition-colors",
        selected
          ? "border-signal bg-signal/10"
          : "border-border bg-surface-raised hover:border-border-strong"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className={cn("text-sm font-medium", selected ? "text-signal" : "text-text-primary")}>
          Level {level.pressure_level} — {level.label}
        </span>
        <span className="text-xs text-text-muted">
          {level.time_limit_seconds ? `${level.time_limit_seconds}s / question` : "No time limit"}
        </span>
      </div>
      <p className="mt-1 text-xs text-text-secondary">{level.description}</p>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {level.characteristics.map((c) => (
          <li key={c} className="rounded-full border border-border px-2 py-0.5 text-[11px] text-text-muted">
            {c}
          </li>
        ))}
      </ul>
    </button>
  );
}
