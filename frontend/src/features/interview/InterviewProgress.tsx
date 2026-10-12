import { ProgressBar } from "@/components/ui/progress";

interface InterviewProgressProps {
  current: number;
  total: number;
}

/** "Question 3 of 10" with a progress bar. */
export function InterviewProgress({ current, total }: InterviewProgressProps) {
  const percent = Math.min(100, Math.round((current / total) * 100));
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs text-text-secondary">
        <span>
          Question {current} of {total}
        </span>
        <span>{percent}%</span>
      </div>
      <ProgressBar value={percent} label="Interview progress" className="h-1.5" />
    </div>
  );
}
