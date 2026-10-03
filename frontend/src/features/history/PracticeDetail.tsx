import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface PracticeQuestionDetail {
  question_id: string;
  question: string;
  type: string | null;
  options: string[] | null;
  answered: boolean;
  answer?: string | null;
  correct?: boolean | null;
  score?: number | null;
  feedback?: string | null;
  missing_points?: string[];
  ideal_answer?: string | null;
  explanation?: string | null;
}

export interface PracticeDetailData {
  topic_title: string | null;
  category: string | null;
  difficulty: string | null;
  status: string | null;
  score: number | null;
  question_count: number;
  questions_answered: number | null;
  correct_answers: number | null;
  weak_areas: string[];
  recommendations: string[];
  questions: PracticeQuestionDetail[];
}

function Stat({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div>
      <p className="font-display text-xl font-semibold text-text-primary">{value}</p>
      <p className="text-xs text-text-muted">{label}</p>
    </div>
  );
}

export function PracticeDetail({ data }: { data: PracticeDetailData }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="grid grid-cols-2 gap-4 py-4 sm:grid-cols-4">
          <Stat label="Score" value={data.score} />
          <Stat label="Questions" value={data.question_count} />
          <Stat label="Answered" value={data.questions_answered} />
          <Stat label="Correct" value={data.correct_answers} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Questions</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-4">
            {data.questions.map((q, index) => (
              <li key={q.question_id} className="space-y-2 border-b border-border pb-4 last:border-b-0 last:pb-0">
                <p className="text-sm font-medium text-text-primary">
                  {index + 1}. {q.question}
                </p>
                {!q.answered ? (
                  <p className="text-xs text-text-muted">Not answered.</p>
                ) : (
                  <div className="space-y-1.5 text-sm">
                    <p className="whitespace-pre-wrap break-words text-text-secondary">
                      <span className="text-text-muted">Your answer: </span>
                      {q.answer}
                    </p>
                    <p className={q.correct ? "text-signal" : "text-warn"}>
                      {q.correct ? "Correct" : "Needs work"}
                      {q.score != null ? ` · ${q.score}/100` : ""}
                    </p>
                    {q.feedback && <p className="text-text-secondary">{q.feedback}</p>}
                    {q.missing_points && q.missing_points.length > 0 && (
                      <ul className="list-disc space-y-0.5 pl-5 text-text-secondary">
                        {q.missing_points.map((p) => (
                          <li key={p}>{p}</li>
                        ))}
                      </ul>
                    )}
                    {q.ideal_answer && (
                      <p className="text-text-secondary">
                        <span className="text-text-muted">Ideal answer: </span>
                        {q.ideal_answer}
                      </p>
                    )}
                    {q.explanation && (
                      <p className="text-text-secondary">
                        <span className="text-text-muted">Explanation: </span>
                        {q.explanation}
                      </p>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      {(data.weak_areas.length > 0 || data.recommendations.length > 0) && (
        <Card>
          <CardContent className="space-y-3 py-4 text-sm">
            {data.weak_areas.length > 0 && (
              <p className="text-text-secondary">
                <span className="text-text-muted">Areas to review: </span>
                {data.weak_areas.join(", ")}
              </p>
            )}
            {data.recommendations.map((r) => (
              <p key={r} className="text-text-secondary">
                {r}
              </p>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
