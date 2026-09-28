import { Check } from "lucide-react";

export function StrengthsCard({ strengths }: { strengths: string[] }) {
  if (strengths.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        Keep practicing — your stronger areas will show up here once a few categories reach a consistently high
        score.
      </p>
    );
  }
  return (
    <ul className="space-y-1.5">
      {strengths.map((area) => (
        <li key={area} className="flex items-center gap-2 text-sm text-text-primary">
          <Check size={14} className="shrink-0 text-signal" />
          {area}
        </li>
      ))}
    </ul>
  );
}
