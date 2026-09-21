import { useState } from "react";
import { QuestionEvaluation } from "@/features/interview/QuestionEvaluation";
import type { AnswerRecord, InterviewQuestion } from "@/types/interview";

function Exchange({ label, question, record }: { label: string; question: string; record: AnswerRecord }) {
  return (
    <div className="space-y-2">
      <div>
        <p className="text-xs font-medium text-text-muted">{label}</p>
        <p className="text-sm text-text-primary">{question}</p>
      </div>
      <div>
        <p className="text-xs font-medium text-text-muted">
          Your Answer:{record.answer_input_type === "voice" ? " (spoken)" : ""}
        </p>
        <p className="whitespace-pre-wrap text-sm text-text-secondary">
          {record.answer ?? "Not answered."}
        </p>
      </div>
      <QuestionEvaluation record={record} />
    </div>
  );
}

/** Detailed per-question review: question, your answer, scores, feedback and an improved answer. */
export function QuestionReview({ questions }: { questions: InterviewQuestion[] }) {
  const [openNumber, setOpenNumber] = useState<number | null>(questions[0]?.question_number ?? null);

  return (
    <ul className="space-y-2">
      {questions.map((q) => {
        const open = openNumber === q.question_number;
        return (
          <li key={q.question_number} className="rounded-[var(--radius-panel)] border border-border">
            <button
              type="button"
              aria-expanded={open}
              onClick={() => setOpenNumber(open ? null : q.question_number)}
              className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left"
            >
              <span className="text-sm text-text-primary">
                <span className="text-text-muted">Q{q.question_number}. </span>
                {q.question}
              </span>
              <span className="shrink-0 text-xs text-text-muted">
                {q.technical_score !== null ? `${q.technical_score} / ${q.communication_score}` : "—"}
              </span>
            </button>
            {open && (
              <div className="space-y-4 border-t border-border px-3 py-3">
                <Exchange label="Question:" question={q.question} record={q} />
                {q.follow_up_questions.map((fu, i) => (
                  <div key={fu.question} className="border-l border-border pl-3">
                    <Exchange label={`Follow-up ${i + 1}:`} question={fu.question} record={fu} />
                  </div>
                ))}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
