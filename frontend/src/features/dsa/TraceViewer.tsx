import { useState } from "react";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { TraceStep } from "@/types/dsa";

/**
 * Step-through view of an algorithm's intermediate states. It is deliberately plain: no animation, so it
 * respects reduced-motion preferences by construction. Buttons and the arrow/Home/End keys move between steps, the
 * current step is announced politely, and "Show all steps" lays the whole trace out as a list.
 */
export function TraceViewer({ steps, title = "Step-by-step trace" }: { steps: TraceStep[]; title?: string }) {
  const [i, setI] = useState(0);
  const [all, setAll] = useState(false);
  if (steps.length === 0) return null;
  const step = steps[Math.min(i, steps.length - 1)];
  const go = (n: number) => setI(Math.max(0, Math.min(steps.length - 1, n)));

  return (
    <section aria-label={title} className="space-y-2 rounded-[var(--radius-panel)] border border-border bg-surface p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-semibold text-text-primary">{title}</h3>
        <button type="button" aria-pressed={all} onClick={() => setAll((v) => !v)} className="text-xs text-link underline-offset-2 hover:underline">
          {all ? "Step through" : "Show all steps"}
        </button>
      </div>

      {all ? (
        <ol className="space-y-1.5">
          {steps.map((s, n) => (
            <li key={n} className="grid gap-x-3 gap-y-0.5 text-xs sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)]">
              <span className="text-text-secondary">{n + 1}. {s.label}</span>
              <code className="break-words font-mono text-text-primary">{s.state}</code>
            </li>
          ))}
        </ol>
      ) : (
        <div
          tabIndex={0}
          role="group"
          aria-label="Trace steps. Use the left and right arrow keys to move."
          onKeyDown={(e) => {
            // These keys belong to the trace while it has focus; stop them reaching the page-level question shortcuts.
            const handled = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? steps.length - 1 : null;
            if (handled !== null) { e.preventDefault(); e.stopPropagation(); go(handled); }
          }}
          className="space-y-2 rounded-[var(--radius-panel)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
        >
          <div aria-live="polite" className="space-y-1 rounded-[var(--radius-panel)] bg-surface-raised px-3 py-2">
            <p className="text-xs text-text-muted">Step {i + 1} of {steps.length}</p>
            <p className="text-sm font-medium text-text-primary">{step.label}</p>
            <code className={cn("block break-words font-mono text-sm text-text-primary")}>{step.state}</code>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <Button type="button" size="sm" variant="secondary" onClick={() => go(0)} disabled={i === 0} aria-label="First step"><ChevronsLeft size={14} aria-hidden="true" /></Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => go(i - 1)} disabled={i === 0}><ChevronLeft size={14} aria-hidden="true" /> Previous</Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => go(i + 1)} disabled={i === steps.length - 1}>Next <ChevronRight size={14} aria-hidden="true" /></Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => go(steps.length - 1)} disabled={i === steps.length - 1} aria-label="Last step"><ChevronsRight size={14} aria-hidden="true" /></Button>
          </div>
        </div>
      )}
    </section>
  );
}
