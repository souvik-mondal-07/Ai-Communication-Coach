import { useState } from "react";
import type { DomainRow, DomainsData, ModeRow } from "@/types/analytics";
import { Empty } from "./AnalyticsStates";
import { bandColor, formatScore } from "./analyticsUtils";

function Bar({ label, score, detail }: { label: string; score: number | null; detail: string }) {
  return (
    <li>
      <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
        <span className="text-text-primary">{label}</span>
        <span className="text-xs text-text-muted">
          {detail} · <span className="text-text-primary">{formatScore(score, "%")}</span>
        </span>
      </div>
      <div className="h-2 rounded-full bg-surface-raised" role="progressbar" aria-label={`${label} score`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={score ?? undefined}>
        <div className="h-2 rounded-full" style={{ width: `${score ?? 0}%`, background: bandColor(score) }} />
      </div>
    </li>
  );
}

export function ModesSection({ modes }: { modes: ModeRow[] }) {
  if (modes.length === 0) return <Empty>No completed interviews in this range yet.</Empty>;
  return (
    <ul className="space-y-3">
      {modes.map((m) => (
        <Bar key={m.mode} label={`${m.label} interview`} score={m.overall_score} detail={`${m.sessions} session${m.sessions === 1 ? "" : "s"}${m.reliable ? "" : " (early)"}`} />
      ))}
    </ul>
  );
}

function DomainList({ title, rows }: { title: string; rows: DomainRow[] }) {
  if (rows.length === 0) return null;
  return (
    <div>
      <h4 className="mb-2 text-xs font-medium text-text-secondary">{title}</h4>
      <ul className="space-y-3">
        {rows.map((d) => (
          <Bar key={d.domain} label={d.domain} score={d.score} detail={`${d.questions} questions`} />
        ))}
      </ul>
    </div>
  );
}

export function DomainsSection({ data }: { data: DomainsData }) {
  const [showAll, setShowAll] = useState(false);
  if (data.domains.length === 0 && data.insufficient_data.length === 0) {
    return <Empty>Practice or interview on a cybersecurity topic to see domain performance.</Empty>;
  }
  const rows = showAll ? data.domains : data.domains.slice(0, 5);
  return (
    <div className="space-y-4">
      {data.domains.length === 0 ? <Empty>No domain has enough scored questions for a percentage yet.</Empty> : <DomainList title="Strongest first" rows={rows} />}
      {data.domains.length > 5 ? (
        <button type="button" onClick={() => setShowAll((v) => !v)} className="text-xs text-link hover:underline">
          {showAll ? "Show fewer" : `Show all ${data.domains.length} domains`}
        </button>
      ) : null}
      {data.insufficient_data.length > 0 ? (
        <details className="text-xs text-text-muted">
          <summary className="cursor-pointer">Not enough data yet ({data.insufficient_data.length})</summary>
          <p className="mt-1">{data.insufficient_data.map((d) => `${d.domain} (${d.questions} q)`).join(", ")}</p>
        </details>
      ) : null}
    </div>
  );
}
