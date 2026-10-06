import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { Comparison, OverviewData } from "@/types/analytics";
import { changeToneClass, formatChange, formatScore } from "./analyticsUtils";

function ScoreTile({ label, value, comparison, hint }: { label: string; value: number | null; comparison?: Comparison; hint?: string }) {
  return (
    <Card>
      <CardContent>
        <p className="text-xs font-medium text-text-secondary">{label}</p>
        <p className="mt-1 font-display text-3xl font-semibold text-text-primary">{formatScore(value)}</p>
        {comparison?.available ? (
          <p className="mt-1 text-xs text-text-muted" title={`Previous ${comparison.previous} → current ${comparison.current}`}>
            Previous {comparison.previous} → {comparison.current}{" "}
            <span className={changeToneClass(comparison.label)}>
              ({formatChange(comparison.change)} · {comparison.label})
            </span>
          </p>
        ) : (
          <p className="mt-1 text-xs text-text-muted">{hint ?? "No previous period to compare"}</p>
        )}
      </CardContent>
    </Card>
  );
}

export function OverviewSection({ data }: { data: OverviewData }) {
  const [open, setOpen] = useState(false);
  const r = data.readiness;
  const cmp = data.comparison.available ? data.comparison : null;
  return (
    <section aria-label="Overview" className="space-y-3">
      <Card>
        <CardContent>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-medium text-text-secondary">Interview readiness</p>
              {r.available ? (
                <p className="mt-1 font-display text-4xl font-semibold text-signal">
                  {r.score}
                  <span className="ml-2 text-base font-medium text-text-secondary">{r.band}</span>
                </p>
              ) : (
                <p className="mt-1 font-display text-2xl font-semibold text-text-muted">{r.message ?? "Not enough data"}</p>
              )}
              <p className="mt-1 max-w-xl text-xs text-text-muted">
                {r.available ? `Based on ${Math.round(r.coverage * 100)}% of the full formula. ` : ""}
                {r.detail}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              className="flex items-center gap-1 text-xs text-link hover:underline"
            >
              How is this calculated? <ChevronDown size={14} className={open ? "rotate-180" : ""} />
            </button>
          </div>
          {open ? (
            <div className="mt-4 border-t border-border pt-3 text-xs text-text-secondary">
              <p className="mb-2">
                Weighted blend (not a plain average): {Object.entries(r.formula).map(([k, w]) => `${k.replace("_", "-")} ×${w}`).join(" · ")}.
                Components without enough data are left out and the weights re-normalised.
              </p>
              <ul className="grid gap-1 sm:grid-cols-2">
                {r.components.map((c) => (
                  <li key={c.label}>
                    {c.label}: <span className="text-text-primary">{c.score}</span> ({c.samples} samples)
                  </li>
                ))}
                {r.missing_components.map((c) => (
                  <li key={c.key} className="text-text-muted">
                    {c.label}: not enough data ({c.samples}/{c.needed})
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <ScoreTile label="Technical score" value={data.scores.technical} comparison={cmp?.technical} />
        <ScoreTile label="Communication score" value={data.scores.communication} comparison={cmp?.communication} />
        <ScoreTile label="Confidence" value={data.scores.confidence} comparison={cmp?.confidence} hint="From communication practice sessions" />
        <ScoreTile label="Interview overall" value={data.scores.overall} comparison={cmp?.overall} />
      </div>
    </section>
  );
}
