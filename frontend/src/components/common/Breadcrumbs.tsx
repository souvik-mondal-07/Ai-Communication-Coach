import { ChevronRight } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { breadcrumbsFor } from "@/components/common/navigation";
import { cn } from "@/lib/utils";

/** Trail for nested pages only (e.g. CTF & Labs / Session). Top-level pages already show a page title. */
export function Breadcrumbs() {
  const crumbs = breadcrumbsFor(useLocation().pathname);
  if (crumbs.length < 2) return null;
  return (
    <nav aria-label="Breadcrumb" className="mb-4 min-w-0">
      <ol className="flex items-center gap-1.5 text-sm">
        {crumbs.map((c, i) => {
          const isLast = i === crumbs.length - 1;
          return (
            <li key={c.label} className={cn("flex min-w-0 items-center gap-1.5", !isLast && "hidden sm:flex")}>
              {c.to && !isLast ? (
                <Link to={c.to} className="rounded text-text-muted transition-colors hover:text-text-primary">
                  {c.label}
                </Link>
              ) : (
                <span aria-current="page" className="truncate font-medium text-text-primary">
                  {c.label}
                </span>
              )}
              {!isLast && <ChevronRight size={14} className="shrink-0 text-text-muted" aria-hidden="true" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
