import type { RecommendationType } from "@/types/progress";

export const TYPE_ROUTE: Record<RecommendationType, string> = {
  practice: "/cybersecurity",
  ctf: "/ctf",
  communication: "/communication",
  interview: "/interview",
  pressure: "/pressure-training",
};

export const TYPE_ACTION_LABEL: Record<RecommendationType, string> = {
  practice: "Start Practice",
  ctf: "Start CTF",
  communication: "Start Communication",
  interview: "Start Interview",
  pressure: "Start Pressure Training",
};
