import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ImprovementList } from "@/features/communication/ImprovementList";
import { CommunicationScoreCard } from "@/features/interview/CommunicationScoreCard";
import { QuestionReview } from "@/features/interview/QuestionReview";
import { RecommendationList } from "@/features/interview/RecommendationList";
import { evaluatedRecords } from "@/features/interview/scoreUtils";
import { TechnicalScoreCard } from "@/features/interview/TechnicalScoreCard";
import { WeaknessList } from "@/features/interview/WeaknessList";
import { SpeakingMetricsGrid } from "@/features/voice/SpeakingPerformancePanel";
import type { InterviewSessionView } from "@/types/interview";
import { INTERVIEW_DIFFICULTY_LABELS, INTERVIEW_TYPE_LABELS } from "@/types/interview";

interface FinalInterviewResultProps {
  session: InterviewSessionView;
  onPracticeAgain: () => void;
  onBack: () => void;
}

/** The end-of-interview results page. */
export function FinalInterviewResult({ session, onPracticeAgain, onBack }: FinalInterviewResultProps) {
  const [showQuestions, setShowQuestions] = useState(false);
  const final = session.final_evaluation;
  if (!final) return null;

  const records = evaluatedRecords(session.questions);

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="text-center">
        <h1 className="font-display text-xl font-semibold text-text-primary">Interview Complete</h1>
        <p className="mt-0.5 text-xs text-text-muted">
          {INTERVIEW_TYPE_LABELS[session.interview_type]} · {INTERVIEW_DIFFICULTY_LABELS[session.difficulty]} ·{" "}
          {final.answered_questions} of {session.question_count} questions answered
        </p>
      </div>

      <Card>
        <CardContent className="py-6 text-center">
          <p className="text-xs text-text-muted">Overall Score</p>
          <p className="mt-1 font-display text-4xl font-semibold text-text-primary" data-testid="overall-score">
            {final.overall_score}
            <span className="text-lg text-text-muted"> / 100</span>
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <TechnicalScoreCard score={final.technical_score} interviewType={session.interview_type} records={records} />
        <CommunicationScoreCard score={final.communication_score} records={records} />
      </div>

      <Card>
        <CardContent className="space-y-3 py-5">
          <p className="text-sm leading-relaxed text-text-secondary">{final.summary}</p>
          {!final.ai_narrative_available && (
            <p className="text-[11px] text-text-muted">
              A written AI summary wasn't available for this interview, so the notes below are based on your
              scores. Every score and the per-question feedback are complete.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardContent className="py-5">
            <ImprovementList title="Strengths" items={final.strengths} variant="positive" />
            {final.strengths.length === 0 && (
              <p className="text-sm text-text-secondary">No standout strengths were recorded.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-5">
            <WeaknessList evaluation={final} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="py-5">
          <RecommendationList evaluation={final} />
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

      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => setShowQuestions((v) => !v)} aria-expanded={showQuestions}>
          {showQuestions ? "Hide Detailed Questions" : "View Detailed Questions"}
        </Button>
        <Button onClick={onPracticeAgain}>Practice Again</Button>
        <Button variant="ghost" onClick={onBack}>
          Back to Interview
        </Button>
      </div>

      {showQuestions && (
        <section aria-label="Question review" className="space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">Question Review</h2>
          <QuestionReview questions={session.questions} />
        </section>
      )}
    </div>
  );
}
