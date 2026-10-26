import { useState } from "react";
import { KeyRound, Link2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ResultTable } from "@/features/dbms-sql/ResultTable";
import type { Dataset } from "@/types/dbmsSql";

interface Props {
  dataset: Dataset | undefined;
  status: "idle" | "loading" | "ready" | "error";
  error: string | null;
  onRetry: () => void;
  /** Click a table name to insert it in the editor, when provided. */
  onPickTable?: (name: string) => void;
}

/** The practice tables: columns with key markers, then every sample row on demand. The data is read-only and the same for everyone. */
export function SchemaViewer({ dataset, status, error, onRetry, onPickTable }: Props) {
  const [open, setOpen] = useState<string | null>(null);
  if (status === "error") return <ErrorState message={error ?? "Unable to load the sample tables."} onRetry={onRetry} />;
  if (!dataset) {
    return <div role="status" aria-label="Loading sample tables" className="space-y-2"><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /><Skeleton className="h-10 w-full" /></div>;
  }
  return (
    <section aria-label="Sample tables" className="space-y-2">
      <p className="text-xs text-text-muted">{dataset.description}</p>
      <ul className="space-y-2">
        {dataset.tables.map((t) => (
          <li key={t.name} className="rounded-[var(--radius-panel)] border border-border bg-surface">
            <div className="flex items-center justify-between gap-2 px-3 py-2">
              {onPickTable ? (
                <button type="button" className="font-mono text-sm font-semibold text-link underline-offset-2 hover:underline" onClick={() => onPickTable(t.name)} aria-label={`Insert ${t.name} into the editor`}>{t.name}</button>
              ) : <span className="font-mono text-sm font-semibold text-text-primary">{t.name}</span>}
              <button type="button" aria-expanded={open === t.name} aria-controls={`rows-${t.name}`} onClick={() => setOpen(open === t.name ? null : t.name)}
                className="text-xs text-link underline-offset-2 hover:underline">{open === t.name ? "Hide rows" : `Show ${t.row_count} rows`}</button>
            </div>
            <p className="px-3 pb-1 text-[11px] text-text-muted">{t.description}</p>
            <ul className="flex flex-wrap gap-1.5 px-3 pb-2.5" aria-label={`${t.name} columns`}>
              {t.columns.map((c) => (
                <li key={c.name}>
                  <Badge tone={c.primary_key ? "info" : c.references ? "violet" : "neutral"} title={c.references ? `Foreign key to ${c.references}` : undefined}>
                    {c.primary_key && <KeyRound size={10} aria-label="primary key" />}
                    {c.references && <Link2 size={10} aria-label={`foreign key to ${c.references}`} />}
                    <span className="font-mono">{c.name}</span> <span className="opacity-70">{c.type}{!c.not_null ? "?" : ""}</span>
                  </Badge>
                </li>
              ))}
            </ul>
            {open === t.name && (
              <div id={`rows-${t.name}`} className="border-t border-border p-2">
                <ResultTable caption={`Sample rows of ${t.name}`} columns={t.columns.map((c) => c.name)} rows={t.rows} rowCount={t.row_count} />
              </div>
            )}
          </li>
        ))}
      </ul>
      <p className="text-[11px] text-text-muted">Key: key icon = primary key, link icon = foreign key, "?" = may be NULL. Indexes: {dataset.indexes.map((i) => i.name).join(", ") || "none"}.</p>
    </section>
  );
}
