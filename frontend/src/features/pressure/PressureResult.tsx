import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ImprovementList } from "@/features/communication/ImprovementList";
import { PressureChat } from "@/features/pressure/PressureChat";
import { SpeakingMetricsGrid } from "@/features/voice/SpeakingPerformancePanel";
import { INTERVIEW_DIFFICULTY_LABELS } from "@/types/interview";
import type { PressureSessionView } from "@/types/pressure";

interface PressureResultProps {
  session: PressureSessionView;
  onPracticeAgain: () => void;
  onBack: () => void;
}

const MODE_LABELS = { interview: "Interview", communication: "Communication" } as const;

function ScoreTile({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-3 text-center">
      <p className="text-[11px] text-text-muted">{label}</p>
      <p className="mt-1 font-display text-xl font-semibold text-text-primary">{value ?? "—"}</p>
    </div>
  );
}

/** The end-of-session results page. Never presents any score as a clinical or diagnostic measurement. */
export function PressureResult({ session, onPracticeAgain, onBack }: PressureResultProps) {
  const [showQuestions, setShowQuestions] = useState(false);
  const final = session.final_evaluation;
  if (!final) return null;

  const comparison = final.comparison;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="text-center">
        <h1 className="font-display text-xl font-semibold text-text-primary">Pressure Training Complete</h1>
        <p className="mt-0.5 text-xs text-text-muted">
          Level {session.pressure_level} · {MODE_LABELS[session.mode]} · {INTERVIEW_DIFFICULTY_LABELS[session.difficulty]}
        </p>
      </div>

      <Card>
        <CardContent className="py-6 text-center">
          <p className="text-xs text-text-muted">Performance Under Pressure</p>
          <p className="mt-1 font-display text-4xl font-semibold text-text-primary" data-testid="overall-score">
            {final.overall_score}
            <span className="text-lg text-text-muted"> / 100</span>
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <ScoreTile label="Technical" value={final.technical_score} />
        <ScoreTile label="Communication" value={final.communication_score} />
        <ScoreTile label={final.pressure_handling_label} value={final.pressure_handling_score} />
        <ScoreTile label="Response Control" value={final.response_control_score} />
      </div>

      <Card>
        <CardContent className="space-y-3 py-5">
          <p className="text-sm leading-relaxed text-text-secondary">{final.summary}</p>
          {!final.ai_narrative_available && (
            <p className="text-[11px] text-text-muted">
              A written AI summary wasn't available for this session, so the notes below are based on your scores.
              Every score and the per-question feedback are complete.
            </p>
          )}
        </CardContent>
      </Card>

      {final.pressure_indicators.length > 0 && (
        <Card>
          <CardContent className="py-5">
            <ImprovementList title="Observed Indicators" items={final.pressure_indicators} variant="neutral" />
            <p className="mt-2 text-[11px] leading-snug text-text-muted">
              Approximate communication observations — not a diagnosis of anxiety, nervousness, or any
              mental-health condition.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardContent className="py-5">
            <ImprovementList title="What Went Well" items={final.strengths} variant="positive" />
            {final.strengths.length === 0 && (
              <p className="text-sm text-text-secondary">No standout strengths were recorded.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-5">
            <ImprovementList title="What To Improve" items={final.areas_to_improve} variant="negative" />
            {final.areas_to_improve.length === 0 && (
              <p className="text-sm text-text-secondary">No specific weaknesses stood out.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {final.recommendations.length > 0 && (
        <Card>
          <CardContent className="py-5">
            <ImprovementList title="Recommended Practice" items={final.recommendations} variant="neutral" />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="space-y-3 py-5">
          <p className="text-xs font-medium text-text-muted">Comparison With Normal Practice</p>
          {!comparison.baseline_available ? (
            <p className="text-sm text-text-secondary">{comparison.message ?? "No baseline available yet."}</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <ScoreTile label="Normal Technical" value={comparison.normal_practice?.technical_score ?? null} />
              <ScoreTile label="Normal Communication" value={comparison.normal_practice?.communication_score ?? null} />
              <ScoreTile
                label="Normal Speaking Rate"
                value={comparison.normal_practice?.speaking_rate_wpm ?? null}
              />
              <ScoreTile label="Normal Filler Words" value={comparison.normal_practice?.filler_words ?? null} />
            </div>
          )}
        </CardContent>
      </Card>

      {final.voice_summary && (
        <Card>
          <CardContent className="space-y-3 py-5">
            <SpeakingMetricsGrid voiceSummary={final.voice_summary} />
            <p className="text-[11px] leading-snug text-text-muted">
              Approximate communication indicators from your spoken answers — not a psychological or medical
              assessment.
            </p>
          </CardContent>
        </Card>
      )}

      {session.self_reported_difficulty && (
        <Card>
          <CardContent className="py-4">
            <p className="text-xs font-medium text-text-muted">How You Reported This Session</p>
            <p className="mt-1 text-sm text-text-primary capitalize">
              {session.self_reported_difficulty.replace("_", " ")}
            </p>
            {session.self_report_note && (
              <p className="mt-1 text-sm text-text-secondary">{session.self_report_note}</p>
            )}
          </CardContent>
        </Card>
      )}

      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => setShowQuestions((v) => !v)} aria-expanded={showQuestions}>
          {showQuestions ? "Hide Detailed Questions" : "View Detailed Questions"}
        </Button>
        <Button onClick={onPracticeAgain}>Practice Again</Button>
        <Button variant="ghost" onClick={onBack}>
          Back to Pressure Training
        </Button>
      </div>

      {showQuestions && (
        <section aria-label="Question review" className="space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">Question Review</h2>
          <PressureChat questions={session.questions} />
        </section>
      )}
    </div>
  );
}
