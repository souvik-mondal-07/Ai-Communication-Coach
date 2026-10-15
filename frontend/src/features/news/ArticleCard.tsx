import { useState } from "react";
import { ExternalLink, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { NewsArticle } from "@/types/news";
import { CATEGORY_TONE, formatPublished, SEVERITY_LABEL, SEVERITY_TONE, safeExternalUrl } from "@/features/news/newsMeta";

/** Accent stripe per category so text-only cards still read as distinct, branded tiles. */
const ACCENT: Record<string, string> = {
  danger: "bg-danger", warn: "bg-warn", info: "bg-signal", violet: "bg-violet", success: "bg-success", neutral: "bg-border-strong",
};

function CardImage({ src }: { src: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) return null; // a broken or blocked image silently falls back to the text-only card
  return (
    <img
      src={src}
      alt=""
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      className="mb-3 aspect-[16/9] w-full rounded-[var(--radius-panel)] border border-border object-cover"
    />
  );
}

interface ArticleCardProps {
  article: NewsArticle;
  categoryLabel?: string;
  now?: Date;
  className?: string;
}

/**
 * One article. Everything shown is plain text from the source (React escapes it; nothing is ever
 * rendered as HTML). Links go to the original article only, and open with noopener noreferrer.
 */
export function ArticleCard({ article, categoryLabel, now, className }: ArticleCardProps) {
  const href = safeExternalUrl(article.url);
  const published = formatPublished(article.published_at, now);
  const tone = CATEGORY_TONE[article.category] ?? "neutral";
  const severity = article.severity;
  const imageSrc = safeExternalUrl(article.image_url);

  return (
    <article
      className={cn(
        "relative flex h-full flex-col overflow-hidden rounded-[var(--radius-card)] border border-border bg-surface p-5 pl-6 shadow-card",
        "transition-[border-color,box-shadow,transform] duration-200 focus-within:border-border-input hover:-translate-y-px hover:border-border-input hover:shadow-pop",
        className
      )}
    >
      <span aria-hidden="true" className={cn("absolute inset-y-0 left-0 w-1", ACCENT[tone])} />
      {imageSrc && imageSrc.startsWith("https://") && <CardImage src={imageSrc} />}

      <div className="flex flex-wrap items-center gap-1.5">
        <Badge tone={tone}>{categoryLabel ?? article.category}</Badge>
        {severity && (
          <Badge tone={SEVERITY_TONE[severity.level]}>
            <ShieldAlert size={11} aria-hidden="true" />
            {SEVERITY_LABEL[severity.level]}
            {severity.score !== null && ` · ${severity.score.toFixed(1)}`}
            <span className="sr-only"> severity, {severity.scheme} as scored by {severity.assigned_by}</span>
          </Badge>
        )}
        {article.cve_ids.slice(0, 2).map((id) => (
          <Badge key={id} tone="neutral" className="font-mono">{id}</Badge>
        ))}
      </div>

      <h3 className="mt-3 font-display text-base font-semibold leading-snug text-text-primary">
        {href ? (
          <a href={href} target="_blank" rel="noopener noreferrer" className="rounded-sm hover:text-link focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal">
            {article.title}
            <span className="sr-only"> (opens the original article in a new tab)</span>
          </a>
        ) : (
          article.title
        )}
      </h3>

      {article.summary && <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-text-secondary">{article.summary}</p>}

      <div className="mt-auto flex flex-wrap items-center justify-between gap-x-3 gap-y-1 pt-4 text-xs text-text-muted">
        <p className="min-w-0">
          <span className="font-medium text-text-secondary">{article.source_name}</span>
          <span aria-hidden="true"> · </span>
          {article.published_at && published ? (
            <time dateTime={article.published_at} title={`Published ${new Date(article.published_at).toUTCString()}`}>{published}</time>
          ) : (
            <span>Publication date not provided</span>
          )}
        </p>
        {href && (
          <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-sm font-medium text-link hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal">
            Read at {article.source_name} <ExternalLink size={12} aria-hidden="true" />
          </a>
        )}
      </div>
    </article>
  );
}
