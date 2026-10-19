import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DataSet } from "@/types/aptitude";

const COLORS = ["var(--color-signal)", "var(--color-violet)", "var(--color-cyan)", "var(--color-amber)", "var(--color-success)", "var(--color-danger)"];

function Table({ caption, columns, rows }: { caption: string; columns: string[]; rows: (string | number)[][] }) {
  return (
    <div className="overflow-x-auto rounded-[var(--radius-panel)] border border-border">
      <table className="w-full min-w-[20rem] border-collapse text-sm">
        <caption className="border-b border-border bg-surface-raised px-3 py-2 text-left text-xs font-medium text-text-secondary">{caption}</caption>
        <thead>
          <tr className="bg-surface-raised/60">
            {columns.map((c) => <th key={c} scope="col" className="px-3 py-2 text-left font-medium text-text-primary">{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-border">
              {r.map((cell, j) => (j === 0
                ? <th key={j} scope="row" className="px-3 py-2 text-left font-medium text-text-primary">{cell}</th>
                : <td key={j} className="px-3 py-2 tabular-nums text-text-secondary">{cell}</td>))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Tables render directly. Charts are drawn without animation and always come with the same numbers as a table, so nothing depends on colour or sight alone. */
export function DataView({ data }: { data: DataSet }) {
  if (data.kind === "table") return <Table caption={data.title} columns={data.columns} rows={data.rows} />;

  if (data.kind === "pie") {
    const rows = data.slices.map((s) => [s.label, `${s.value}${data.unit}`]);
    return (
      <figure className="space-y-2">
        <figcaption className="text-xs font-medium text-text-secondary">{data.title}</figcaption>
        <div className="h-56" aria-hidden="true">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data.slices} dataKey="value" nameKey="label" outerRadius={85} isAnimationActive={false} label={(p) => `${p.name} ${p.value}${data.unit}`}>
                {data.slices.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <details className="text-sm">
          <summary className="cursor-pointer text-xs text-link">View values as a table</summary>
          <div className="mt-2"><Table caption={data.title} columns={["Category", "Share"]} rows={rows} /></div>
        </details>
      </figure>
    );
  }

  const chartRows = data.categories.map((cat, i) => ({ name: cat, ...Object.fromEntries(data.series.map((s) => [s.name, s.values[i]])) }));
  const tableRows = data.categories.map((cat, i) => [cat, ...data.series.map((s) => s.values[i])]);
  return (
    <figure className="space-y-2">
      <figcaption className="text-xs font-medium text-text-secondary">{data.title}</figcaption>
      <div className="h-60" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          {data.kind === "bar" ? (
            <BarChart data={chartRows} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} />
              <YAxis stroke="var(--color-text-muted)" fontSize={11} />
              <Tooltip />
              {data.series.length > 1 && <Legend />}
              {data.series.map((s, i) => <Bar key={s.name} dataKey={s.name} fill={COLORS[i % COLORS.length]} isAnimationActive={false} />)}
            </BarChart>
          ) : (
            <LineChart data={chartRows} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} />
              <YAxis stroke="var(--color-text-muted)" fontSize={11} />
              <Tooltip />
              {data.series.length > 1 && <Legend />}
              {data.series.map((s, i) => <Line key={s.name} type="monotone" dataKey={s.name} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot isAnimationActive={false} />)}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-text-muted">{data.x_label} (horizontal) · {data.y_label} (vertical)</p>
      <details className="text-sm">
        <summary className="cursor-pointer text-xs text-link">View values as a table</summary>
        <div className="mt-2"><Table caption={data.title} columns={[data.x_label, ...data.series.map((s) => s.name)]} rows={tableRows} /></div>
      </details>
    </figure>
  );
}
