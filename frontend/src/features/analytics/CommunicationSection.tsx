import type { CommunicationData, SpeakingData } from "@/types/analytics";
import { Empty } from "./AnalyticsStates";
import { bandColor, formatScore, WEAKNESS_SEVERITY_CLASS } from "./analyticsUtils";

const LENGTH_LABEL = { too_short: "Too short", appropriate: "Appropriate", long: "Long", very_long: "Very long" } as const;
const NOT_TRACKED_LABEL: Record<string, string> = {
  self_corrections: "self-corrections",
  incomplete_sentences: "incomplete sentences",
  weak_opening_statement: "opening statements",
  weak_conclusion: "conclusions",
};

export function CommunicationSection({ data }: { data: CommunicationData }) {
  if (data.dimensions.length === 0) return <Empty>No evaluated answers or communication sessions in this range yet.</Empty>;
  const length = data.length.available ? data.length : null;
  return (
    <div className="space-y-5">
      <ul className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
        {data.dimensions.map((d) => (
          <li key={d.key}>
            <div className="mb-1 flex justify-between text-sm">
              <span className="capitalize text-text-primary">{d.key}</span>
              <span className="text-text-secondary">{d.score}</span>
            </div>
            <div className="h-2 rounded-full bg-surface-raised" role="progressbar" aria-label={`${d.key} score`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={d.score}>
              <div className="h-2 rounded-full" style={{ width: `${d.score}%`, background: bandColor(d.score) }} />
            </div>
          </li>
        ))}
      </ul>

      {length ? (
        <div>
          <h4 className="mb-1 text-xs font-medium text-text-secondary">Answer length</h4>
          <p className="text-sm text-text-primary">
            Average {length.average_words} words (min {length.min_words}, max {length.max_words})
            {length.average_duration_seconds ? ` · ${length.average_duration_seconds}s spoken` : ""}
          </p>
          <p className="mt-1 text-xs text-text-muted">
            {(Object.keys(LENGTH_LABEL) as (keyof typeof LENGTH_LABEL)[]).map((k) => `${LENGTH_LABEL[k]}: ${length.distribution[k]}`).join(" · ")}
          </p>
          <p className="mt-1 text-xs text-text-muted">{length.note}</p>
        </div>
      ) : null}

      {data.structure.by_kind.length > 0 ? (
        <div>
          <h4 className="mb-1 text-xs font-medium text-text-secondary">Answer structure by question type</h4>
          <ul className="space-y-1 text-sm text-text-primary">
            {data.structure.by_kind.map((k) => (
              <li key={k.kind}>
                <span className="capitalize">{k.kind}</span>: structure score {formatScore(k.structure_score)}
                {k.marker_coverage !== null ? ` · ${Math.round(k.marker_coverage * 100)}% of expected stages present` : ""}
                <span className="text-text-muted"> ({k.answers} answers)</span>
              </li>
            ))}
          </ul>
          <p className="mt-1 text-xs text-text-muted">{data.structure.note}</p>
        </div>
      ) : null}
    </div>
  );
}

export function WeaknessList({ items }: { items: CommunicationData["weaknesses"] }) {
  if (items.length === 0) {
    return <Empty>No recurring weakness detected. A weakness needs repeated evidence across several answers.</Empty>;
  }
  return (
    <ul className="space-y-3">
      {items.map((w) => (
        <li key={w.id}>
          <p className="text-sm text-text-primary">
            {w.label} <span className={`text-xs ${WEAKNESS_SEVERITY_CLASS[w.severity]}`}>({w.severity})</span>
          </p>
          <p className="text-xs text-text-muted">{w.evidence}</p>
        </li>
      ))}
    </ul>
  );
}

export function SpeakingSection({ data }: { data: SpeakingData }) {
  if (!data.available || !data.metrics) return <Empty>{data.message ?? "No voice answers yet."} Speaking metrics need recorded answers.</Empty>;
  const m = data.metrics;
  const tiles: [string, string][] = [
    ["Words per minute", formatScore(m.words_per_minute)],
    ["Filler words / 100 words", formatScore(m.filler_per_100_words)],
    ["Pauses per minute", formatScore(m.pauses_per_minute)],
    ["Long pauses", formatScore(m.long_pauses)],
    ["Avg answer length", m.average_answer_seconds === null ? "N/A" : `${m.average_answer_seconds}s`],
  ];
  return (
    <div>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {tiles.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs text-text-muted">{label}</dt>
            <dd className="font-display text-xl font-semibold text-text-primary">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-text-muted">
        Based on {m.spoken_answers} spoken answers. Treat single recordings lightly; the trend chart is more telling.
        Not tracked yet: {data.not_tracked.map((k) => NOT_TRACKED_LABEL[k] ?? k).join(", ")}.
      </p>
    </div>
  );
}
