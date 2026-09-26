import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { SELF_REPORT_OPTIONS, type SelfReportedDifficulty } from "@/types/pressure";

interface SelfReportProps {
  onSubmit: (difficulty: SelfReportedDifficulty, note?: string) => Promise<void>;
  isSaving: boolean;
  savedValue: SelfReportedDifficulty | null;
}

/** Optional self-report shown after a session ends. Entirely the user's own account of how it felt. */
export function SelfReport({ onSubmit, isSaving, savedValue }: SelfReportProps) {
  const [selected, setSelected] = useState<SelfReportedDifficulty | null>(savedValue);
  const [note, setNote] = useState("");
  const [submitted, setSubmitted] = useState(savedValue !== null);

  if (submitted) {
    return (
      <Card>
        <CardContent className="py-4 text-sm text-text-secondary">Thanks — your feedback was saved.</CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="space-y-3 py-5">
        <p className="text-sm font-medium text-text-primary">How did this session feel?</p>
        <div role="radiogroup" aria-label="How did this session feel?" className="flex flex-wrap gap-2">
          {SELF_REPORT_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={selected === option.value}
              onClick={() => setSelected(option.value)}
              className={cn(
                "rounded-[var(--radius-panel)] border px-3 py-1.5 text-sm transition-colors",
                selected === option.value
                  ? "border-signal bg-signal/15 font-medium text-signal"
                  : "border-border bg-surface-raised text-text-secondary hover:border-border-strong"
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
        <label className="block space-y-1">
          <span className="text-xs text-text-muted">What made it difficult? (optional)</span>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            maxLength={1000}
            placeholder="Optional notes…"
            className="w-full resize-y rounded-[var(--radius-panel)] border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
          />
        </label>
        <Button
          disabled={!selected || isSaving}
          onClick={async () => {
            if (!selected) return;
            await onSubmit(selected, note.trim() || undefined);
            setSubmitted(true);
          }}
        >
          {isSaving ? "Saving…" : "Save"}
        </Button>
      </CardContent>
    </Card>
  );
}
