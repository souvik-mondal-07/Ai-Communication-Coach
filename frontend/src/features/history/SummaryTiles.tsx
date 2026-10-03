import { Card } from "@/components/ui/card";
import type { HistorySummary } from "@/types/history";

/** Real, all-time counts from the user's own sessions; types with no activity are omitted. */
export function SummaryTiles({ summary }: { summary: HistorySummary }) {
  const tiles = [
    { key: "total", label: "Total activities", count: summary.total },
    ...summary.types.filter((t) => t.count > 0).map((t) => ({ key: t.type, label: t.label, count: t.count })),
  ];
  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4" aria-label="Activity totals">
      {tiles.map((tile, index) => (
        <li key={tile.key}>
          <Card className={index === 0 ? "border-signal/40" : undefined}>
            <div className="px-4 py-3">
              <p className="font-display text-2xl font-semibold text-text-primary">{tile.count}</p>
              <p className="text-xs text-text-muted">{tile.label}</p>
            </div>
          </Card>
        </li>
      ))}
    </ul>
  );
}
