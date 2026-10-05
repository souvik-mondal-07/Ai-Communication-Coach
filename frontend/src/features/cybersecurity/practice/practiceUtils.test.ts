import { describe, expect, it } from "vitest";
import type { PracticeQuestionState } from "@/features/cybersecurity/cybersecurityTypes";
import { firstOpenIndex, formatClock, nextHintStep, progressBar } from "./practiceUtils";

const q = (answered: boolean, over: Partial<PracticeQuestionState> = {}): PracticeQuestionState => ({
  question_id: Math.random().toString(),
  index: 0,
  question: "?",
  type: "scenario",
  options: null,
  topic_title: "T",
  category: "Linux",
  difficulty: "beginner",
  hints_available: 3,
  hints_used: 0,
  hints: [],
  answered,
  result: null,
  ...over,
});

describe("practiceUtils", () => {
  it("formats the clock", () => {
    expect(formatClock(125)).toBe("02:05");
    expect(formatClock(-5)).toBe("00:00");
  });

  it("draws the progress bar", () => {
    expect(progressBar(2, 5)).toBe("████░░░░░░ 2/5");
    expect(progressBar(0, 0)).toContain("0/0");
  });

  it("resumes at the first unanswered question, else the last", () => {
    expect(firstOpenIndex([q(true), q(false), q(false)])).toBe(1);
    expect(firstOpenIndex([q(true), q(true)])).toBe(1);
    expect(firstOpenIndex([])).toBe(0);
  });

  it("walks the hint ladder: hint -> hint -> hint -> explanation", () => {
    expect(nextHintStep(q(false, { hints_used: 0 }), 3)).toBe("hint");
    expect(nextHintStep(q(false, { hints_used: 2 }), 3)).toBe("hint");
    expect(nextHintStep(q(false, { hints_used: 3 }), 3)).toBe("explanation");
    expect(nextHintStep(q(true), 3)).toBe("none");
    expect(nextHintStep(q(false, { hints_available: 0 }), 3)).toBe("none");
  });
});

import { recommendationRoute } from "./practiceUtils";

describe("recommendationRoute", () => {
  const base = { title: "t", topic: "x", reasons: [], basis: null, source: "personalization" as const };
  it("opens the recommended topic at its difficulty", () => {
    expect(recommendationRoute({ ...base, topic_slug: "xss", difficulty: "intermediate" })).toBe(
      "/cybersecurity/xss?difficulty=intermediate"
    );
  });
  it("falls back to the practice page", () => {
    expect(recommendationRoute({ ...base, topic_slug: null, difficulty: null })).toBe("/practice");
  });
});
