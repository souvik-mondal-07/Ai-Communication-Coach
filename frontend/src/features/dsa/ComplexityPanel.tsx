import type { Complexity } from "@/types/dsa";

const LABELS: Record<string, string> = { time: "Time", space: "Auxiliary space", best: "Best case", average: "Average case", worst: "Worst case" };
const ORDER = ["time", "space", "best", "average", "worst"];

/** Time/space and best/average/worst notes. Theoretical complexity only: these are not measured run times. */
export function ComplexityPanel({ complexity }: { complexity: Complexity | null }) {
  if (!complexity) return null;
  const keys = [...ORDER.filter((k) => k in complexity), ...Object.keys(complexity).filter((k) => !ORDER.includes(k))];
  if (keys.length === 0) return null;
  return (
    <section aria-label="Complexity analysis" className="rounded-[var(--radius-panel)] border border-border bg-surface px-3 py-2.5">
      <h3 className="text-xs font-semibold text-text-primary">Complexity analysis</h3>
      <dl className="mt-1.5 grid gap-x-4 gap-y-1 text-xs sm:grid-cols-2">
        {keys.map((k) => (
          <div key={k} className="flex gap-2"><dt className="shrink-0 text-text-muted">{LABELS[k] ?? k}:</dt><dd className="font-mono text-text-primary">{complexity[k]}</dd></div>
        ))}
      </dl>
      <p className="mt-1.5 text-[11px] text-text-muted">Theoretical growth rates, not measured run times: real timings depend on the machine, language and input.</p>
    </section>
  );
}
