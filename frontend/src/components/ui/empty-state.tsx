import type { LucideIcon } from "lucide-react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  /** A button or link that tells the user what to do next. */
  action?: ReactNode;
  className?: string;
}

/** An empty screen is an invitation to act: say what's missing and offer the next step. */
export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center gap-3 px-4 py-10 text-center", className)}>
      {Icon && (
        <div className="flex h-11 w-11 items-center justify-center rounded-full border border-border bg-surface-raised text-text-secondary">
          <Icon size={20} aria-hidden="true" />
        </div>
      )}
      <p className="text-sm font-medium text-text-primary">{title}</p>
      {description && <p className="max-w-sm text-sm text-text-muted">{description}</p>}
      {action}
    </div>
  );
}

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

/** Says what went wrong and how to recover. Announced to screen readers via role="alert". */
export function ErrorState({ message, onRetry, className }: ErrorStateProps) {
  return (
    <div role="alert" className={cn("flex flex-wrap items-center gap-3 text-sm", className)}>
      <AlertTriangle size={16} className="shrink-0 text-danger" aria-hidden="true" />
      <p className="text-danger">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <RefreshCw size={13} aria-hidden="true" /> Retry
        </Button>
      )}
    </div>
  );
}
