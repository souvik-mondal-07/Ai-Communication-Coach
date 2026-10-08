/**
 * Profile & account types (Step 14). Option lists are the single source for both
 * the UI and the value types, and mirror the enums in backend `app/schemas/user.py`.
 */

export interface Option<V extends string = string> {
  value: V;
  label: string;
  description?: string;
}

export const EXPERIENCE_LEVELS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
] as const satisfies readonly Option[];

export const CYBERSECURITY_INTERESTS = [
  { value: "web_security", label: "Web Security" },
  { value: "penetration_testing", label: "Penetration Testing" },
  { value: "red_teaming", label: "Red Teaming" },
  { value: "soc", label: "SOC" },
  { value: "siem", label: "SIEM" },
  { value: "digital_forensics", label: "Digital Forensics" },
  { value: "incident_response", label: "Incident Response" },
  { value: "threat_intelligence", label: "Threat Intelligence" },
  { value: "network_security", label: "Network Security" },
  { value: "cloud_security", label: "Cloud Security" },
  { value: "malware_analysis", label: "Malware Analysis" },
  { value: "active_directory", label: "Active Directory" },
  { value: "ctf", label: "CTF" },
  { value: "cryptography", label: "Cryptography" },
  { value: "security_research", label: "Security Research" },
] as const satisfies readonly Option[];

export const LEARNING_GOALS = [
  { value: "improve_penetration_testing", label: "Improve penetration testing" },
  { value: "learn_web_security", label: "Learn web security" },
  { value: "prepare_for_interviews", label: "Prepare for cybersecurity interviews" },
  { value: "improve_networking", label: "Improve networking fundamentals" },
  { value: "learn_soc_siem", label: "Learn SOC/SIEM" },
  { value: "practice_ctfs", label: "Practice CTFs" },
  { value: "improve_linux", label: "Improve Linux skills" },
  { value: "improve_active_directory", label: "Improve Active Directory skills" },
  { value: "improve_communication", label: "Improve communication" },
] as const satisfies readonly Option[];

export const RESPONSE_STYLES = [
  { value: "simple", label: "Simple", description: "Beginner-friendly explanations in plain language." },
  { value: "balanced", label: "Balanced", description: "Clear explanations with moderate technical depth." },
  { value: "technical", label: "Technical", description: "Detailed terminology and deeper technical reasoning." },
] as const satisfies readonly Option[];

export const LEARNING_DIFFICULTIES = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
  { value: "adaptive", label: "Adaptive", description: "The mentor adjusts difficulty gradually from your recent results." },
] as const satisfies readonly Option[];

export const LEARNING_STYLES = [
  { value: "explanation", label: "Explanation", description: "Walk me through the concepts." },
  { value: "practical", label: "Practical", description: "Real-world examples and scenarios." },
  { value: "question_based", label: "Question based", description: "Quiz me and learn from the answers." },
  { value: "hands_on", label: "Hands-on", description: "Labs and exercises first." },
  { value: "mixed", label: "Mixed", description: "A bit of everything." },
] as const satisfies readonly Option[];

export const INTERVIEW_FOCUS_AREAS = [
  { value: "hr", label: "HR" },
  { value: "behavioral", label: "Behavioral" },
  { value: "cybersecurity_technical", label: "Cybersecurity Technical" },
  { value: "soc", label: "SOC" },
  { value: "blue_team", label: "Blue Team" },
  { value: "red_team", label: "Red Team" },
  { value: "penetration_testing", label: "Penetration Testing" },
  { value: "networking", label: "Networking" },
  { value: "linux", label: "Linux" },
  { value: "web_security", label: "Web Security" },
  { value: "scenario_based", label: "Scenario Based" },
  { value: "resume_based", label: "Resume Based" },
] as const satisfies readonly Option[];

export const THEMES = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
] as const satisfies readonly Option[];

type ValueOf<T extends readonly Option[]> = T[number]["value"];

export type ExperienceLevel = ValueOf<typeof EXPERIENCE_LEVELS>;
export type CybersecurityInterest = ValueOf<typeof CYBERSECURITY_INTERESTS>;
export type LearningGoal = ValueOf<typeof LEARNING_GOALS>;
export type ResponseStyle = ValueOf<typeof RESPONSE_STYLES>;
export type LearningDifficulty = ValueOf<typeof LEARNING_DIFFICULTIES>;
export type LearningStyle = ValueOf<typeof LEARNING_STYLES>;
export type InterviewFocus = ValueOf<typeof INTERVIEW_FOCUS_AREAS>;
export type ThemePreference = ValueOf<typeof THEMES>;

export const MAX_CUSTOM_GOALS = 5;
export const FIELD_LIMITS = { name: 100, bio: 500, education: 150, careerGoal: 100, customGoal: 100 } as const;

export interface ProfileData {
  bio: string;
  education: string;
  career_goal: string;
  experience_level: ExperienceLevel | null;
  cybersecurity_interests: CybersecurityInterest[];
  learning_goals: LearningGoal[];
  custom_learning_goals: string[];
}

export type Weekday = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";

export const WEEKDAYS: readonly { value: Weekday; label: string }[] = [
  { value: "mon", label: "Mon" },
  { value: "tue", label: "Tue" },
  { value: "wed", label: "Wed" },
  { value: "thu", label: "Thu" },
  { value: "fri", label: "Fri" },
  { value: "sat", label: "Sat" },
  { value: "sun", label: "Sun" },
];

/** Daily practice lengths offered in Settings (the API accepts any whole number of minutes from 5 to 120). */
export const PRACTICE_MINUTE_OPTIONS = [5, 10, 15, 20, 30, 45, 60] as const;

export interface UserPreferences {
  response_style: ResponseStyle;
  difficulty: LearningDifficulty;
  learning_style: LearningStyle;
  interview_focus: InterviewFocus[];
  theme: ThemePreference;
  // Step 19 -- practice & notification preferences
  daily_practice_enabled: boolean;
  daily_practice_minutes: number;
  preferred_practice_time: string; // "HH:MM", 24-hour, in preferred_timezone
  preferred_timezone: string | null; // IANA name; null until chosen
  practice_days: Weekday[];
  reminders_enabled: boolean;
  interview_reminders_enabled: boolean;
  communication_reminders_enabled: boolean;
  cybersecurity_reminders_enabled: boolean;
  browser_notifications_enabled: boolean;
}

export interface CompletionItem {
  key: string;
  label: string;
  done: boolean;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  profile: ProfileData;
  preferences: UserPreferences;
  completion: { percentage: number; items: CompletionItem[] };
}

/** PATCH /users/me body — only these keys exist, mirroring the backend allow-list. */
export type ProfileUpdate = Partial<{ full_name: string } & ProfileData>;
export type PreferencesUpdate = Partial<UserPreferences>;

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
  confirm_new_password: string;
}
