import { cn } from "@/lib/utils";
import type { Option } from "@/types/profile";

interface ChipSelectProps<V extends string> {
  options: readonly Option<V>[];
  value: readonly V[];
  onChange: (next: V[]) => void;
  label: string;
}

/** Multi-select rendered as toggle chips (accessible: each chip is a pressed/unpressed button). */
export function ChipSelect<V extends string>({ options, value, onChange, label }: ChipSelectProps<V>) {
  function toggle(v: V) {
    onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v]);
  }
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((o) => {
        const selected = value.includes(o.value);
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={selected}
            onClick={() => toggle(o.value)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-sm transition-colors",
              selected
                ? "border-signal bg-signal/15 text-signal"
                : "border-border text-text-secondary hover:border-border-strong hover:text-text-primary"
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
