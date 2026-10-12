import { TYPE_ROUTE } from "@/features/progress/recommendationRoutes";
import type { Priority, ProgressOverview, RecommendationType } from "@/types/progress";

export interface Step {
  key: string;
  title: string;
  description: string;
  to: string;
  type: RecommendationType;
  /** Set only for items that come from the user's own recommendations. */
  priority?: Priority;
}

/** Starting points shown when the user has no recommendation of that type. They are NOT personalised. */
const GENERAL: Step[] = [
  { key: "g-practice", type: "practice", title: "Complete OWASP Top 10", description: "Learn about the most critical web vulnerabilities.", to: "/cybersecurity" },
  { key: "g-interview", type: "interview", title: "Practice Interview Questions", description: "Improve your technical and behavioral answers.", to: "/interview" },
  { key: "g-communication", type: "communication", title: "Try a Communication Scenario", description: "Build confidence in real-world situations.", to: "/communication" },
  { key: "g-ctf", type: "ctf", title: "Start a CTF Challenge", description: "Test your skills with a hands-on challenge.", to: "/ctf" },
];

/** Real recommendations first (max 4), padded with clearly-general suggestions of other types. */
export function buildSteps(overview: ProgressOverview | null): { steps: Step[]; personalised: boolean } {
  const real: Step[] = (overview?.recommendations ?? [])
    .filter((r) => !r.completed)
    .slice(0, 4)
    .map((r) => ({ key: r._id, type: r.type, title: r.area, description: r.reason, to: TYPE_ROUTE[r.type], priority: r.priority }));
  const used = new Set(real.map((s) => s.type));
  const filler = GENERAL.filter((g) => !used.has(g.type));
  return { steps: [...real, ...filler].slice(0, 4), personalised: real.length > 0 };
}
