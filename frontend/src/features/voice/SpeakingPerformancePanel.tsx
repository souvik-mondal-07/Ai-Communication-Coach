import { Card, CardContent } from "@/components/ui/card";
import { ImprovementList } from "@/features/communication/ImprovementList";
import { ScoreCard } from "@/features/communication/ScoreCard";
import type { VoiceSummary } from "@/features/voice/voiceTypes";

interface SpeakingPerformancePanelProps {
  voiceSummary: VoiceSummary;
  /** From the main (Step 7) evaluation. */
  overallScore: number;
  conversationFlowScore: number;
}

const RATE_GUIDANCE: Record<string, string> = {
  slow: "a little slower than typical conversation",
  moderate: "a comfortable conversational range",
  fast: "a little faster than typical conversation",
};

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2.5">
      <p className="font-display text-lg font-semibold text-text-primary">{value}</p>
      <p className="mt-0.5 text-[11px] text-text-muted">{label}</p>
      {hint && <p className="mt-0.5 text-[11px] text-text-secondary">{hint}</p>}
    </div>
  );
}

export function SpeakingPerformancePanel({
  voiceSummary: v,
  overallScore,
  conversationFlowScore,
}: SpeakingPerformancePanelProps) {
  const fillerHint = Object.entries(v.filler_words)
    .slice(0, 3)
    .map(([word, count]) => `“${word}” ×${count}`)
    .join(", ");

  const pauseValue =
    v.pause_count === null
      ? "Not measured"
      : v.longest_pause_seconds === null
        ? "None detected"
        : `${v.longest_pause_seconds} sec`;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-text-primary">Speaking Performance</h3>

      <Card>
        <CardContent className="py-5 text-center">
          <p className="text-xs text-text-muted">Overall Communication</p>
          <p className="mt-1 font-display text-3xl font-semibold text-text-primary">
            {overallScore}
            <span className="text-base text-text-muted">/100</span>
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-5">
        <ScoreCard label="Clarity" score={v.clarity_score} />
        <ScoreCard label="Grammar" score={v.grammar_score} />
        <ScoreCard label="Vocabulary" score={v.vocabulary_score} />
        <ScoreCard label="Conciseness" score={v.conciseness_score} />
        <ScoreCard label="Conversation Flow" score={conversationFlowScore} />
      </div>

      <div>
        <p className="mb-1.5 text-xs font-medium text-text-muted">Speaking Metrics</p>
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          <Metric
            label="Speaking Rate"
            value={v.average_speaking_rate_wpm === null ? "Not measured" : `${v.average_speaking_rate_wpm} WPM`}
            hint={v.speaking_rate_label ? RATE_GUIDANCE[v.speaking_rate_label] : undefined}
          />
          <Metric label="Filler Words" value={String(v.total_filler_words)} hint={fillerHint || undefined} />
          <Metric label="Longest Pause" value={pauseValue} />
          <Metric label="Words Spoken" value={String(v.total_words_spoken)} />
        </div>
      </div>

      <Card>
        <CardContent className="space-y-4 py-5">
          <ImprovementList title="What You Did Well" items={v.strengths} variant="positive" />
          <ImprovementList title="What To Improve" items={v.improvements} variant="neutral" />
          {v.summary && <p className="text-sm leading-relaxed text-text-secondary">{v.summary}</p>}
        </CardContent>
      </Card>

      <p className="text-[11px] leading-snug text-text-muted">
        These are approximate communication indicators based on your transcript and recording timing
        (pace bands of roughly 100–160 WPM are general guidance, not a standard). They are not a
        psychological, medical, or clinical assessment.
        {!v.ai_feedback_available &&
          " AI feedback wasn't available for this session, so scores reflect measured metrics only and grammar isn't scored."}
      </p>
    </div>
  );
}
