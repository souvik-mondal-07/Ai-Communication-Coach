import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusMessage, type Flash } from "@/features/profile/StatusMessage";

interface SectionCardProps {
  title: string;
  description?: string;
  children: ReactNode;
  /** Omit to render a read-only card with no footer. */
  onSave?: () => void;
  isSaving?: boolean;
  isDirty?: boolean;
  saveLabel?: string;
  savingLabel?: string;
  flash?: Flash | null;
  onDismissFlash?: () => void;
}

/** Card with a heading, form body and a save footer that blocks duplicate submits. */
export function SectionCard({
  title,
  description,
  children,
  onSave,
  isSaving = false,
  isDirty = true,
  saveLabel = "Save changes",
  savingLabel = "Saving...",
  flash = null,
  onDismissFlash = () => {},
}: SectionCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <p className="mt-1 text-xs text-text-muted">{description}</p>}
      </CardHeader>
      <CardContent className="space-y-5">
        {children}
        {onSave && (
          <div className="flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0 flex-1">
              <StatusMessage flash={flash} onDismiss={onDismissFlash} />
            </div>
            <Button type="button" onClick={onSave} disabled={isSaving || !isDirty} className="sm:shrink-0">
              {isSaving ? savingLabel : saveLabel}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
