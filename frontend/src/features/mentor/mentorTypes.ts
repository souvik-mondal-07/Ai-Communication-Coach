export type MentorMode = "learn" | "explain" | "practice" | "troubleshoot";
export type MentorLevel = "beginner" | "intermediate" | "advanced";

export const MENTOR_MODES: { value: MentorMode; label: string }[] = [
  { value: "learn", label: "Learn" },
  { value: "explain", label: "Explain" },
  { value: "practice", label: "Practice" },
  { value: "troubleshoot", label: "Troubleshoot" },
];

export const MENTOR_LEVELS: { value: MentorLevel; label: string }[] = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

export const MENTOR_EXAMPLE_PROMPTS: string[] = [
  "What is the difference between TCP and UDP?",
  "Teach me Linux file permissions.",
  "How does SQL injection work?",
  "Help me understand a failed Nmap scan.",
  "Give me a beginner networking quiz.",
];
