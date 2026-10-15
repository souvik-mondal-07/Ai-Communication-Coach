import { ShieldAlert } from "lucide-react";
import type { NewsArticle } from "@/types/news";
import { ArticleCard } from "@/features/news/ArticleCard";

/**
 * "Featured" here has an objective basis: NVD scored these CVEs as critical. It renders only when
 * such items exist (and only on the unfiltered view); there is no editorial ranking behind it.
 */
export function CriticalStrip({ items, now }: { items: NewsArticle[]; now?: Date }) {
  if (items.length === 0) return null;
  return (
    <section aria-labelledby="critical-heading" className="rounded-[var(--radius-card)] border border-danger/25 bg-danger/5 p-4 md:p-5">
      <h2 id="critical-heading" className="flex items-center gap-2 font-display text-sm font-semibold text-text-primary">
        <ShieldAlert size={16} className="text-danger" aria-hidden="true" />
        Critical-severity CVEs this week
      </h2>
      <p className="mt-1 text-xs text-text-muted">Scored critical by NIST&apos;s National Vulnerability Database. Severity is the published CVSS score, not our opinion.</p>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {items.map((a) => (
          <ArticleCard key={a.id} article={a} categoryLabel="Vulnerability" now={now} />
        ))}
      </div>
    </section>
  );
}
