import type { AnswerRecord, InterviewQuestion } from "@/types/interview";

/** Every answered prompt (main answers and follow-ups) that has an evaluation. */
export function evaluatedRecords(questions: InterviewQuestion[]): AnswerRecord[] {
  return questions
    .flatMap((q) => [q as AnswerRecord, ...q.follow_up_questions])
    .filter((r) => r.answer !== null && r.technical_evaluation !== null && r.communication_evaluation !== null);
}

/** Mean of one evaluation dimension across records, or null if none have it. */
export function averageOf(
  records: AnswerRecord[],
  kind: "technical_evaluation" | "communication_evaluation",
  key: string
): number | null {
  const values = records
    .map((r) => (r[kind] as unknown as Record<string, number | null> | null)?.[key])
    .filter((v): v is number => typeof v === "number");
  return values.length ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : null;
}
