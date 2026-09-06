import { MENTOR_LEVELS, type MentorLevel } from "@/features/mentor/mentorTypes";

interface LevelSelectorProps {
  value: MentorLevel;
  onChange: (level: MentorLevel) => void;
  disabled?: boolean;
}

export function LevelSelector({ value, onChange, disabled }: LevelSelectorProps) {
  return (
    <label className="flex items-center gap-2 text-xs text-text-secondary">
      Level
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value as MentorLevel)}
        className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-2 py-1.5 text-sm text-text-primary disabled:cursor-not-allowed disabled:opacity-60"
        aria-label="Mentor level"
      >
        {MENTOR_LEVELS.map((level) => (
          <option key={level.value} value={level.value}>
            {level.label}
          </option>
        ))}
      </select>
    </label>
  );
}
