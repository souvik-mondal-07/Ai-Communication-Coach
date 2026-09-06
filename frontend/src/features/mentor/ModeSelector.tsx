import { MENTOR_MODES, type MentorMode } from "@/features/mentor/mentorTypes";

interface ModeSelectorProps {
  value: MentorMode;
  onChange: (mode: MentorMode) => void;
  disabled?: boolean;
}

export function ModeSelector({ value, onChange, disabled }: ModeSelectorProps) {
  return (
    <label className="flex items-center gap-2 text-xs text-text-secondary">
      Mode
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value as MentorMode)}
        className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-2 py-1.5 text-sm text-text-primary disabled:cursor-not-allowed disabled:opacity-60"
        aria-label="Mentor mode"
      >
        {MENTOR_MODES.map((mode) => (
          <option key={mode.value} value={mode.value}>
            {mode.label}
          </option>
        ))}
      </select>
    </label>
  );
}
