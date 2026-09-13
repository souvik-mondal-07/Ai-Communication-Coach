import {
  CATEGORY_LABELS,
  DIFFICULTY_LABELS,
  MODE_LABELS,
  type Category,
  type Difficulty,
  type Mode,
} from "@/features/communication/communicationTypes";

interface ScenarioFiltersProps {
  category: Category | "all";
  onCategoryChange: (value: Category | "all") => void;
  mode: Mode | "all";
  onModeChange: (value: Mode | "all") => void;
  difficulty: Difficulty | "all";
  onDifficultyChange: (value: Difficulty | "all") => void;
}

export function ScenarioFilters({
  category,
  onCategoryChange,
  mode,
  onModeChange,
  difficulty,
  onDifficultyChange,
}: ScenarioFiltersProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <label className="flex items-center gap-2 text-xs text-text-secondary">
        Category
        <select
          value={category}
          onChange={(e) => onCategoryChange(e.target.value as Category | "all")}
          className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-2 py-2 text-sm text-text-primary"
        >
          <option value="all">All</option>
          {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-xs text-text-secondary">
        Mode
        <select
          value={mode}
          onChange={(e) => onModeChange(e.target.value as Mode | "all")}
          className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-2 py-2 text-sm text-text-primary"
        >
          <option value="all">All</option>
          {Object.entries(MODE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-xs text-text-secondary">
        Difficulty
        <select
          value={difficulty}
          onChange={(e) => onDifficultyChange(e.target.value as Difficulty | "all")}
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
