import { useState } from "react";
import type { InterviewQuestion } from "@/types/interview";

interface InterviewChatProps {
  questions: InterviewQuestion[];
}

/** Earlier questions and answers, collapsed by default so the current question stays the focus. */
export function InterviewChat({ questions }: InterviewChatProps) {
  const [open, setOpen] = useState(false);
  const answered = questions.filter((q) => q.answer !== null);
  if (answered.length === 0) return null;

  return (
    <div className="rounded-[var(--radius-panel)] border border-border">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-xs text-text-secondary hover:text-text-primary"
      >
        <span>Previous questions ({answered.length})</span>
        <span aria-hidden="true">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <ul className="space-y-3 border-t border-border px-3 py-3">
          {answered.map((q) => (
            <li key={q.question_number} className="space-y-1.5 text-sm">
              <p className="text-text-primary">
                <span className="text-text-muted">Q{q.question_number}. </span>
                {q.question}
              </p>
              <p className="whitespace-pre-wrap pl-3 text-text-secondary">{q.answer}</p>
              {q.follow_up_questions
                .filter((fu) => fu.answer !== null)
                .map((fu) => (
                  <div key={fu.question} className="space-y-1 border-l border-border pl-3">
                    <p className="text-text-primary">
                      <span className="text-text-muted">Follow-up. </span>
                      {fu.question}
                    </p>
                    <p className="whitespace-pre-wrap text-text-secondary">{fu.answer}</p>
                  </div>
                ))}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
