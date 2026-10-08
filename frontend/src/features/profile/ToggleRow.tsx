import { hintClass } from "@/features/profile/formStyles";
import { cn } from "@/lib/utils";

/** Accessible on/off switch row. */
export function ToggleRow({
  label,
  description,
  checked,
  onChange,
  disabled = false,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="text-sm font-medium text-text-primary">{label}</p>
        {description && <p className={hintClass}>{description}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative mt-0.5 h-6 w-11 shrink-0 rounded-full border transition-colors disabled:opacity-50",
          checked ? "border-signal bg-signal/30" : "border-border bg-surface-raised"
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-4.5 w-4.5 rounded-full transition-all",
            checked ? "left-[1.35rem] bg-signal" : "left-0.5 bg-text-muted"
          )}
          style={{ height: "1.1rem", width: "1.1rem" }}
        />
      </button>
    </div>
  );
}

