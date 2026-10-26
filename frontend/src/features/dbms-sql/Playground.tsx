import { useState } from "react";
import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RunOutput, SqlEditor } from "@/features/dbms-sql/SqlWorkbench";
import { SchemaViewer } from "@/features/dbms-sql/SchemaViewer";
import type { Dataset, RunResult, SqlEngine } from "@/types/dbmsSql";

interface Props {
  dataset: Dataset | undefined;
  datasetStatus: "idle" | "loading" | "ready" | "error";
  datasetError: string | null;
  engine: SqlEngine | undefined;
  result: RunResult | null;
  busy: boolean;
  error: string | null;
  onRun: (sql: string) => void;
  onRetryDataset: () => void;
}

const EXAMPLE = "SELECT d.dept_name, COUNT(e.emp_id) AS headcount\nFROM departments d\nLEFT JOIN employees e ON e.dept_id = d.dept_id\nGROUP BY d.dept_id, d.dept_name\nORDER BY d.dept_name;";

/** Free exploration of the sample tables. Nothing here is scored or saved: it is the same isolated read-only sandbox the exercises use. */
export function Playground({ dataset, datasetStatus, datasetError, engine, result, busy, error, onRun, onRetryDataset }: Props) {
  const [sql, setSql] = useState(EXAMPLE);
  const run = () => { if (sql.trim() && !busy) onRun(sql); };
  const insert = (name: string) => setSql((s) => `${s}${s && !s.endsWith(" ") && !s.endsWith("\n") ? " " : ""}${name}`);
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-4">
        <Card><CardHeader><CardTitle>SQL playground</CardTitle></CardHeader><CardContent className="space-y-3">
          <SqlEditor id="playground-sql" value={sql} onChange={setSql} onRun={run} label="Try a query on the sample tables" />
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" onClick={run} loading={busy} disabled={!sql.trim()}><Play size={14} aria-hidden="true" /> Run query</Button>
            <span className="text-xs text-text-muted">Not scored or saved.{engine ? ` Runs on ${engine.engine} ${engine.version}; at most ${engine.limits.max_rows} rows and ${engine.limits.max_seconds}s per query.` : ""}</span>
          </div>
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          {result && <RunOutput run={result} />}
        </CardContent></Card>
        <Card variant="raised"><CardContent className="space-y-1 py-3 text-xs leading-relaxed text-text-secondary">
          <p><span className="font-medium text-text-primary">Supported:</span> one SELECT / WITH / VALUES statement with joins, GROUP BY, HAVING, subqueries, set operators, CTEs (including recursive), window functions and EXPLAIN QUERY PLAN.</p>
          <p><span className="font-medium text-text-primary">Rejected:</span> INSERT, UPDATE, DELETE, DDL, PRAGMA, ATTACH, multiple statements, system tables and file or extension functions. Other products' syntax (TOP, NVL, stored procedures) is not supported here.</p>
        </CardContent></Card>
      </div>
      <aside aria-label="Sample tables"><SchemaViewer dataset={dataset} status={datasetStatus} error={datasetError} onRetry={onRetryDataset} onPickTable={insert} /></aside>
    </div>
  );
}
