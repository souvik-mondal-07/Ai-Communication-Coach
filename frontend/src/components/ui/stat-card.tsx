import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface StatCardProps {
  label: string;
  /** Real value from the API, already formatted. Use "—" only when the API has no value. */
  value: ReactNode;
  hint?: ReactNode;
  icon?: LucideIcon;
  loading?: boolean;
}

export function StatCard({ label, value, hint, icon: Icon, loading = false }: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 py-5">
        <div className="min-w-0">
          <p className="text-xs text-text-muted">{label}</p>
          {loading ? (
            <div role="status" aria-label={`Loading ${label}`} className="mt-2 space-y-2">
              <Skeleton className="h-7 w-16" />
              <Skeleton className="h-3 w-28" />
            </div>
          ) : (
            <>
              <p className="mt-1.5 font-display text-2xl font-semibold tabular-nums text-text-primary">{value}</p>
              {hint && <p className="mt-1 text-xs text-text-secondary">{hint}</p>}
            </>
          )}
        </div>
        {Icon && (
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-panel)] bg-surface-raised text-text-secondary">
            <Icon size={16} aria-hidden="true" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
