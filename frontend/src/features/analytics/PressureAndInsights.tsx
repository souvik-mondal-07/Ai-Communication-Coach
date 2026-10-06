import { Link } from "react-router-dom";
import { Check } from "lucide-react";
import type { InsightsData, PressureData } from "@/types/analytics";
import { Empty } from "./AnalyticsStates";
import { formatChange, formatScore } from "./analyticsUtils";

export function PressureSection({ data }: { data: PressureData }) {
  if (!data.available || !data.pressure) return <Empty>{data.message ?? "No pressure sessions yet."}</Empty>;
  const rows: [string, number | null | undefined, number | null | undefined, number | undefined][] = [
    ["Technical", data.normal?.technical, data.pressure.technical, data.differences.technical],
    ["Communication", data.normal?.communication, data.pressure.communication, data.differences.communication],
    ["Confidence", data.normal?.confidence, data.pressure.confidence, undefined],
  ];
  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <caption className="sr-only">Normal interviews compared with pressure sessions</caption>
          <thead>
            <tr className="text-left text-xs text-text-muted">
              <th className="py-1 pr-4 font-medium">Metric</th>
              <th className="py-1 pr-4 font-medium">Normal</th>
              <th className="py-1 pr-4 font-medium">Pressure</th>
              <th className="py-1 font-medium">Difference</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, normal, pressure, diff]) => (
              <tr key={label} className="border-t border-border">
                <td className="py-1.5 pr-4 text-text-primary">{label}</td>
                <td className="py-1.5 pr-4">{formatScore(normal)}</td>
                <td className="py-1.5 pr-4">{formatScore(pressure)}</td>
                <td className="py-1.5">{formatChange(diff)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-text-muted">
        Pressure handling score: {formatScore(data.pressure_handling_score)}. Confidence is only recorded in communication sessions, so it is not compared here.
      </p>
      {data.comparison_available === false && data.message ? <p className="text-sm text-warn">{data.message}</p> : null}
      {data.insights.map((t) => (
        <p key={t} className="text-sm text-text-primary">{t}</p>
      ))}
    </div>
  );
}

export function InsightsSection({ data }: { data: InsightsData }) {
  if (data.insights.length === 0 && data.next_actions.length === 0) {
    return <Empty>Insights appear once there is enough evidence. Keep practising.</Empty>;
  }
  return (
    <div className="space-y-5">
      {data.ai_summary ? <p className="rounded-[var(--radius-panel)] bg-surface-raised p-3 text-sm text-text-primary">{data.ai_summary}</p> : null}
      <ul className="space-y-2">
        {data.insights.map((i) => (
          <li key={i.text} className="text-sm text-text-primary">
            {i.text}
            <span className="block text-xs text-text-muted">Evidence: {i.evidence}</span>
          </li>
        ))}
      </ul>
      {data.next_actions.length > 0 ? (
        <div>
          <h4 className="mb-2 text-xs font-medium text-text-secondary">What to practise next</h4>
          <ul className="space-y-2">
            {data.next_actions.map((a) => (
              <li key={a.weakness + a.action} className="text-sm">
                <span className="text-text-muted">{a.weakness} →</span>{" "}
                <Link to={a.route} className="text-link hover:underline">{a.action}</Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export function StrengthsList({ items }: { items: string[] }) {
  if (items.length === 0) return <Empty>Strengths show up once an area is consistently strong.</Empty>;
  return (
    <ul className="space-y-1.5">
      {items.map((s) => (
        <li key={s} className="flex items-center gap-2 text-sm text-text-primary">
          <Check size={14} className="shrink-0 text-signal" /> {s}
        </li>
      ))}
    </ul>
  );
}
