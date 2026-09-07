import { Search } from "lucide-react";
import { DIFFICULTY_LABELS, type Difficulty } from "@/features/cybersecurity/cybersecurityTypes";

interface TopicFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  category: string | "all";
  onCategoryChange: (value: string | "all") => void;
  categories: string[];
  difficulty: Difficulty | "all";
  onDifficultyChange: (value: Difficulty | "all") => void;
}

export function TopicFilters({
  search,
  onSearchChange,
  category,
  onCategoryChange,
  categories,
  difficulty,
  onDifficultyChange,
}: TopicFiltersProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="relative flex-1">
        <Search
          size={15}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
        />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search topics..."
          aria-label="Search topics"
          className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised py-2 pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted"
        />
      </div>

      <label className="flex items-center gap-2 text-xs text-text-secondary">
        Category
        <select
          value={category}
          onChange={(e) => onCategoryChange(e.target.value)}
          aria-label="Filter by category"
          className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-2 py-2 text-sm text-text-primary"
        >
          <option value="all">All</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-xs text-text-secondary">
        Difficulty
        <select
          value={difficulty}
          onChange={(e) => onDifficultyChange(e.target.value as Difficulty | "all")}
          aria-label="Filter by difficulty"
          className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-2 py-2 text-sm text-text-primary"
        >
          <option value="all">All</option>
          {Object.entries(DIFFICULTY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
