import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface PlaceholderPageProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

/**
 * Shared "coming soon" shell for feature pages that only have routing +
 * layout in Step 1. Swapped out for the real feature UI as each one is built.
 */
export function PlaceholderPage({ icon: Icon, title, description }: PlaceholderPageProps) {
  return (
    <div className="mx-auto max-w-2xl">
      <Card>
        <CardContent className="flex flex-col items-start gap-4 py-10">
          <div className="flex h-11 w-11 items-center justify-center rounded-[var(--radius-panel)] bg-signal/10 text-signal">
            <Icon size={22} strokeWidth={2} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
            <p className="mt-1.5 text-sm leading-relaxed text-text-secondary">
              {description}
            </p>
          </div>
          <span className="rounded-full border border-border px-2.5 py-1 text-[11px] font-medium text-text-muted">
            Coming in a later step
          </span>
        </CardContent>
      </Card>
    </div>
  );
}
