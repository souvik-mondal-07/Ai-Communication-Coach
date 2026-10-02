import { cn } from "@/lib/utils";
import type { Option } from "@/types/profile";

interface OptionGroupProps<V extends string> {
  options: readonly Option<V>[];
  value: V;
  onChange: (next: V) => void;
  label: string;
}

/** Single-select radio cards with an optional description under each label. */
export function OptionGroup<V extends string>({ options, value, onChange, label }: OptionGroupProps<V>) {
  return (
    <div role="radiogroup" aria-label={label} className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {options.map((o) => {
        const selected = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(o.value)}
            className={cn(
              "rounded-[var(--radius-panel)] border px-3 py-2.5 text-left transition-colors",
              selected ? "border-signal bg-signal/10" : "border-border hover:border-border-strong"
            )}
          >
            <span className={cn("block text-sm font-medium", selected ? "text-signal" : "text-text-primary")}>
              {o.label}
            </span>
            {"description" in o && o.description && (
              <span className="mt-0.5 block text-xs text-text-muted">{o.description}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
