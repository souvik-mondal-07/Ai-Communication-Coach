import { PartyPopper } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { DailySummary } from "@/types/dailyPractice";

function Score({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2">
      <dt className="text-[11px] text-text-muted">{label}</dt>
      <dd className="font-display text-lg font-semibold text-text-primary">{value ?? "—"}</dd>
    </div>
  );
}

/** Completion summary. Every value is read from the finished sessions; nothing is estimated. */
export function DailySummaryCard({ summary, partial }: { summary: DailySummary; partial: boolean }) {
  return (
    <Card>
      <CardContent className="space-y-4 py-5">
        <div className="flex items-center gap-2">
          <PartyPopper size={18} className="text-signal" aria-hidden="true" />
          <h3 className="text-base font-semibold text-text-primary">
            {partial ? "Today's practice saved" : "Today's Practice Complete"}
          </h3>
        </div>
        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Score label="Technical score" value={summary.technical_score} />
          <Score label="Communication" value={summary.communication_score} />
          <Score label="Minutes practiced" value={summary.minutes_practiced} />
          <Score label="Streak (days)" value={summary.streak} />
        </dl>
        {summary.topics.length > 0 && (
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">Topics</p>
            <ul className="mt-1 list-disc space-y-0.5 pl-4 text-sm capitalize text-text-secondary">
              {summary.topics.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
        )}
        {summary.recommended_next && (
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">Recommended next</p>
            <p className="mt-0.5 text-sm text-text-primary">{summary.recommended_next}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
