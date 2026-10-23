import { Badge } from "@/components/ui/badge";
import { formatArgs, formatValue } from "@/features/dsa/dsaMeta";
import type { FullTestCase, TestCase } from "@/types/dsa";

type Row = TestCase & Partial<Pick<FullTestCase, "visible" | "edge">>;

/** Test cases as a table. `expected` values come from the server only for visible tests (before submission) or all tests (after). */
export function TestTable({ tests, caption, hiddenCount = 0 }: { tests: Row[]; caption: string; hiddenCount?: number }) {
  return (
    <div className="space-y-1.5">
      <div className="overflow-x-auto rounded-[var(--radius-panel)] border border-border">
        <table className="w-full min-w-[28rem] text-left text-xs">
          <caption className="sr-only">{caption}</caption>
          <thead className="bg-surface-raised text-text-muted">
            <tr><th scope="col" className="px-3 py-1.5 font-medium">Case</th><th scope="col" className="px-3 py-1.5 font-medium">Input</th><th scope="col" className="px-3 py-1.5 font-medium">Expected output</th></tr>
          </thead>
          <tbody className="divide-y divide-border">
            {tests.map((t) => (
              <tr key={t.label}>
                <td className="px-3 py-1.5 text-text-primary">
                  {t.label}
                  {t.edge && <Badge tone="neutral" className="ml-1.5">edge</Badge>}
                  {t.visible === false && <Badge tone="warn" className="ml-1.5">was hidden</Badge>}
                </td>
                <td className="px-3 py-1.5 font-mono text-text-primary">{formatArgs(t.args)}</td>
                <td className="px-3 py-1.5 font-mono text-text-primary">{formatValue(t.expected)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {hiddenCount > 0 && <p className="text-xs text-text-muted">{hiddenCount} more hidden test case{hiddenCount === 1 ? "" : "s"} (including edge cases) are revealed after you submit.</p>}
    </div>
  );
}
