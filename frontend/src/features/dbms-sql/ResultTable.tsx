import type { Cell } from "@/types/dbmsSql";
import { formatCell } from "@/features/dbms-sql/dbmsSqlMeta";
import { cn } from "@/lib/utils";

interface Props {
  caption: string;
  columns: string[];
  rows: Cell[][];
  /** Total rows the server found (rows may be clipped for display). */
  rowCount?: number;
  truncated?: boolean;
  className?: string;
}

/**
 * A query result as a real table: column headers are <th scope="col">, NULL is shown in words (never an empty cell), numbers are
 * right-aligned, and wide results scroll inside their own container so the page itself never scrolls sideways.
 */
export function ResultTable({ caption, columns, rows, rowCount, truncated, className }: Props) {
  const total = rowCount ?? rows.length;
  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="max-h-72 overflow-auto rounded-[var(--radius-panel)] border border-border">
        <table className="w-full border-collapse text-left text-xs">
          <caption className="sr-only">{caption}</caption>
          <thead className="sticky top-0 bg-surface-raised">
            <tr>
              {columns.map((c, i) => (
                <th key={`${c}-${i}`} scope="col" className="whitespace-nowrap border-b border-border px-3 py-2 font-mono font-semibold text-text-primary">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan={Math.max(1, columns.length)} className="px-3 py-3 text-text-muted">No rows returned.</td></tr>
            ) : rows.map((row, r) => (
              <tr key={r} className="border-b border-border last:border-0">
                {row.map((cell, c) => (
                  <td key={c} className={cn("whitespace-nowrap px-3 py-1.5 font-mono", typeof cell === "number" && "text-right tabular-nums", cell === null ? "italic text-text-muted" : "text-text-primary")}>{formatCell(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-text-muted" aria-live="polite">
        {total} row{total === 1 ? "" : "s"}{truncated || total > rows.length ? ` · showing the first ${rows.length}` : ""}
      </p>
    </div>
  );
}
