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
        className="rounded-[var(--radius-panel)] border border-border-input bg-base/60 px-2 py-1.5 text-sm text-text-primary disabled:cursor-not-allowed disabled:opacity-60 transition-[border-color,box-shadow] focus-visible:border-signal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/30 aria-[invalid=true]:border-danger"
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
