import { Search, X } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { Select } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { NewsCategoriesResponse, NewsCategoryId, NewsSourceInfo } from "@/types/news";
import type { NewsFilters } from "@/features/news/useNewsFeed";

interface NewsToolbarProps {
  filters: NewsFilters;
  onChange: (next: NewsFilters) => void;
  categories: NewsCategoriesResponse | null;
  sources: NewsSourceInfo[];
  searching: boolean;
}

export function NewsToolbar({ filters, onChange, categories, sources, searching }: NewsToolbarProps) {
  const select = (category: NewsCategoryId | null) => onChange({ ...filters, category });
  const chip = (active: boolean) =>
    cn(
      "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal",
      active ? "border-signal bg-signal/15 text-signal" : "border-border bg-surface text-text-secondary hover:border-border-input hover:text-text-primary"
    );

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <div role="search" className="relative flex-1">
          <label htmlFor="news-search" className="sr-only">Search cybersecurity news</label>
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" aria-hidden="true" />
          <input
            id="news-search"
            type="search"
            value={filters.q}
            maxLength={100}
            autoComplete="off"
            placeholder="Search headlines, summaries or a CVE ID…"
            onChange={(e) => onChange({ ...filters, q: e.target.value })}
            className="w-full rounded-[var(--radius-panel)] border border-border-input bg-base/60 py-2 pl-9 pr-9 text-sm text-text-primary placeholder:text-text-muted focus-visible:border-signal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal/30"
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2" aria-live="polite">
            {searching ? <><Spinner size={14} /><span className="sr-only">Searching…</span></> : filters.q ? (
              <button type="button" aria-label="Clear search" onClick={() => onChange({ ...filters, q: "" })} className="rounded-sm text-text-muted hover:text-text-primary focus-visible:outline-2 focus-visible:outline-signal">
                <X size={14} aria-hidden="true" />
              </button>
            ) : null}
          </span>
        </div>
        {sources.length > 0 && (
          <div className="sm:w-56">
            <label htmlFor="news-source" className="sr-only">Filter by source</label>
            <Select id="news-source" value={filters.source ?? ""} onChange={(e) => onChange({ ...filters, source: e.target.value || null })}>
              <option value="">All sources</option>
              {sources.map((s) => (<option key={s.id} value={s.id}>{s.name}</option>))}
            </Select>
          </div>
        )}
      </div>

      <nav aria-label="News categories">
        <ul className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
          <li>
            <button type="button" aria-pressed={filters.category === null} onClick={() => select(null)} className={chip(filters.category === null)}>
              All{categories && <span className="text-text-muted">{categories.total}</span>}
            </button>
          </li>
          {(categories?.categories ?? []).filter((c) => c.id !== "general").map((c) => (
            <li key={c.id}>
              <button type="button" aria-pressed={filters.category === c.id} onClick={() => select(c.id)} title={c.description} className={chip(filters.category === c.id)}>
                {c.label}<span className="text-text-muted">{c.count}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
