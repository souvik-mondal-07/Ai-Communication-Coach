import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: ReactNode;
  icon?: LucideIcon;
  /** Buttons/filters aligned to the right on wide screens, wrapping below on narrow ones. */
  actions?: ReactNode;
  className?: string;
}

/** The single <h1> of a page. Every route uses this so titles look and behave the same. */
export function PageHeader({ title, description, icon: Icon, actions, className }: PageHeaderProps) {
  return (
    <header className={cn("flex flex-wrap items-end justify-between gap-x-6 gap-y-3", className)}>
      <div className="min-w-0 max-w-2xl">
        <h1 className="flex items-center gap-2.5 font-display text-2xl font-semibold text-text-primary">
          {Icon && (
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-panel)] bg-signal/10 text-signal">
              <Icon size={17} aria-hidden="true" />
            </span>
          )}
          <span className="min-w-0">{title}</span>
        </h1>
        {description && <p className="mt-2 text-sm leading-relaxed text-text-secondary">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}
