import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DateRangePreset, HistoryFilters, HistorySort, HistorySummary } from "@/types/history";
import { isInvalidCustomRange, RANGE_LABELS, TYPE_META } from "@/features/history/historyMeta";

const field =
  "h-9 rounded-[var(--radius-panel)] border border-border bg-surface px-3 text-sm text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal";

interface Props {
  filters: HistoryFilters;
  summary: HistorySummary | null;
  /** Typed text, shown immediately; the page debounces it into `filters.search`. */
  searchText: string;
  onSearchText: (value: string) => void;
  onChange: (patch: Partial<HistoryFilters>) => void;
}

export function HistoryToolbar({ filters, summary, searchText, onSearchText, onChange }: Props) {
  // Only categories that actually have data get a tab.
  const tabs = [
    { value: "all" as const, label: "All" },
    ...(summary?.types ?? [])
      .filter((t) => t.count > 0)
      .map((t) => ({ value: t.type, label: TYPE_META[t.type].tab })),
  ];

  return (
    <div className="space-y-3">
      <div role="tablist" aria-label="Activity type" className="flex flex-wrap gap-1.5">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={filters.type === tab.value}
            onClick={() => onChange({ type: tab.value })}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal",
              filters.type === tab.value
                ? "border-signal bg-signal/10 text-signal"
                : "border-border text-text-secondary hover:border-border-strong hover:text-text-primary"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="relative min-w-0 flex-1 sm:min-w-56">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" aria-hidden="true" />
          <input
            type="search"
            value={searchText}
            onChange={(e) => onSearchText(e.target.value)}
            placeholder="Search title or topic, e.g. Linux"
            aria-label="Search activity"
            maxLength={100}
            className={cn(field, "w-full pl-9")}
          />
        </div>

        <select
          value={filters.range}
          onChange={(e) => onChange({ range: e.target.value as DateRangePreset })}
          aria-label="Date range"
          className={field}
        >
          {(Object.keys(RANGE_LABELS) as DateRangePreset[]).map((key) => (
            <option key={key} value={key}>
              {RANGE_LABELS[key]}
            </option>
          ))}
        </select>

        <select
          value={filters.sort}
          onChange={(e) => onChange({ sort: e.target.value as HistorySort })}
          aria-label="Sort order"
          className={field}
        >
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </select>
      </div>

      {filters.range === "custom" && (
        <div className="flex flex-wrap items-center gap-2 text-sm text-text-secondary">
          <label className="flex items-center gap-2">
            From
            <input
              type="date"
              value={filters.customStart}
              max={filters.customEnd || undefined}
              onChange={(e) => onChange({ customStart: e.target.value })}
              className={field}
            />
          </label>
          <label className="flex items-center gap-2">
            To
            <input
              type="date"
              value={filters.customEnd}
              min={filters.customStart || undefined}
              onChange={(e) => onChange({ customEnd: e.target.value })}
              className={field}
            />
          </label>
          {isInvalidCustomRange(filters) && (
            <p role="alert" className="text-xs text-danger">
              The start date must be before the end date.
            </p>
          )}
        </div>
      )}

      {(searchText || filters.range !== "all") && (
        <button
          type="button"
          onClick={() => {
            onSearchText("");
            onChange({ search: "", range: "all", customStart: "", customEnd: "" });
          }}
          className="inline-flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary"
        >
          <X size={13} aria-hidden="true" /> Clear search and date filters
        </button>
      )}
    </div>
  );
}
