import type { Streak } from "@/types/dailyPractice";

export function goalPercent(done: number, goal: number): number {
  if (goal <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((done / goal) * 100)));
}

export function streakHeadline(streak: Streak): string {
  const n = streak.current_streak;
  return n > 0 ? `${n} Day Streak` : "No streak yet";
}

export function streakHint(streak: Streak): string {
  if (streak.current_streak === 0) {
    return streak.total_active_days > 0
      ? "Practice today to start a new streak."
      : "Finish one practice activity today to start your streak.";
  }
  return streak.practiced_today ? "You've practiced today. Nice work." : "Practice today to keep it going.";
}
