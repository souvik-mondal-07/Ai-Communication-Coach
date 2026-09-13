import { ArrowDown } from "lucide-react";
import type { BetterResponse } from "@/features/communication/communicationTypes";

interface BetterResponseCardProps {
  response: BetterResponse;
}

export function BetterResponseCard({ response }: BetterResponseCardProps) {
  return (
    <div className="space-y-2 rounded-[var(--radius-panel)] border border-border bg-surface-raised p-3.5">
      <div>
        <p className="mb-1 text-[11px] font-medium text-text-muted">Your Response</p>
        <p className="text-sm text-text-secondary">"{response.original}"</p>
      </div>
      <div className="flex justify-center text-text-muted">
        <ArrowDown size={14} />
      </div>
      <div>
        <p className="mb-1 text-[11px] font-medium text-signal">Improved Response</p>
        <p className="text-sm text-text-primary">"{response.improved}"</p>
      </div>
      {response.why && (
        <div className="border-t border-border pt-2">
          <p className="mb-1 text-[11px] font-medium text-text-muted">Why This Is Better</p>
          <p className="text-sm text-text-secondary">{response.why}</p>
        </div>
      )}
    </div>
  );
}
