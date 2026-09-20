import { cn } from "@/lib/utils";
import type { InputMode } from "@/features/voice/voiceTypes";

interface InputModeToggleProps {
  value: InputMode;
  onChange: (mode: InputMode) => void;
  voiceSupported: boolean;
  disabled?: boolean;
}

/** `[ Text ] [ Voice ]` selector for how the user answers in a practice session. */
export function InputModeToggle({ value, onChange, voiceSupported, disabled }: InputModeToggleProps) {
  const options: { mode: InputMode; label: string }[] = [
    { mode: "text", label: "Text" },
    { mode: "voice", label: "Voice" },
  ];

  return (
    <div className="inline-flex rounded-[var(--radius-panel)] border border-border bg-surface p-0.5" role="group" aria-label="Response mode">
      {options.map(({ mode, label }) => {
        const unavailable = mode === "voice" && !voiceSupported;
        return (
          <button
            key={mode}
            type="button"
            aria-pressed={value === mode}
            disabled={disabled || unavailable}
            title={unavailable ? "Voice mode isn't supported in this browser" : undefined}
            onClick={() => onChange(mode)}
            className={cn(
              "rounded-[4px] px-3 py-1 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50",
              value === mode
                ? "bg-signal/15 font-medium text-signal"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
