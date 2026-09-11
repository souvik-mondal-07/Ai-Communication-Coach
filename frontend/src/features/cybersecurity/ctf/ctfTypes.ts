export type ChallengeCategory =
  | "web_security"
  | "cryptography"
  | "digital_forensics"
  | "steganography"
  | "osint"
  | "reverse_engineering"
  | "binary_exploitation"
  | "linux"
  | "networking"
  | "miscellaneous";

export type Platform = "Hack The Box" | "TryHackMe" | "CTF" | "Custom Lab" | "Other";
export type CtfDifficulty = "easy" | "medium" | "hard";
export type SessionStatus = "in_progress" | "completed" | "abandoned";
export type HintLevel = "hint_1" | "hint_2" | "hint_3" | "solution";

export interface CtfSessionSummary {
  session_id: string;
  platform: Platform;
  category: ChallengeCategory;
  difficulty: CtfDifficulty;
  title: string;
  status: SessionStatus;
  hints_used: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface CtfChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface CtfHint {
  level: HintLevel;
  content: string;
  requested_at: string;
}

export interface CtfSessionDetail extends CtfSessionSummary {
  description: string;
  user_notes: string;
  messages: CtfChatMessage[];
  hints: CtfHint[];
}

export const CATEGORY_LABELS: Record<ChallengeCategory, string> = {
  web_security: "Web Security",
  cryptography: "Cryptography",
  digital_forensics: "Digital Forensics",
  steganography: "Steganography",
  osint: "OSINT",
  reverse_engineering: "Reverse Engineering",
  binary_exploitation: "Binary/Exploitation Concepts",
  linux: "Linux",
  networking: "Networking",
  miscellaneous: "Miscellaneous",
};

export const PLATFORMS: Platform[] = ["Hack The Box", "TryHackMe", "CTF", "Custom Lab", "Other"];

export const DIFFICULTY_LABELS: Record<CtfDifficulty, string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
};

export const HINT_LEVELS: { level: HintLevel; label: string }[] = [
  { level: "hint_1", label: "Hint 1" },
  { level: "hint_2", label: "Hint 2" },
  { level: "hint_3", label: "Hint 3" },
  { level: "solution", label: "Solution" },
];
