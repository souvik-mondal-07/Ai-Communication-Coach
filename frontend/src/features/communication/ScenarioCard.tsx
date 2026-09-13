import { MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DIFFICULTY_LABELS,
  MODE_LABELS,
  type ScenarioSummary,
} from "@/features/communication/communicationTypes";

interface ScenarioCardProps {
  scenario: ScenarioSummary;
  onStart: (scenarioId: string) => void;
  disabled?: boolean;
}

const DIFFICULTY_STYLES: Record<string, string> = {
  beginner: "text-signal border-signal/30 bg-signal/10",
  intermediate: "text-warn border-warn/30 bg-warn/10",
  advanced: "text-danger border-danger/30 bg-danger/10",
};

export function ScenarioCard({ scenario, onStart, disabled }: ScenarioCardProps) {
  return (
    <Card className="flex flex-col">
      <CardContent className="flex flex-1 flex-col gap-3 py-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold text-text-primary">{scenario.title}</h3>
          <span
            className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium ${
              DIFFICULTY_STYLES[scenario.difficulty] ?? DIFFICULTY_STYLES.intermediate
            }`}
          >
            {DIFFICULTY_LABELS[scenario.difficulty]}
          </span>
        </div>
        <p className="text-xs text-text-muted">{MODE_LABELS[scenario.mode]}</p>
        <p className="flex-1 text-sm text-text-secondary">{scenario.description}</p>
        <p className="text-xs text-text-muted">
          <span className="font-medium text-text-secondary">Objective: </span>
          {scenario.objective}
        </p>
        {scenario.skills_targeted.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {scenario.skills_targeted.slice(0, 3).map((skill) => (
              <span
                key={skill}
                className="rounded-full bg-surface-raised px-2 py-0.5 text-[10px] text-text-muted"
              >
                {skill.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        )}
        <Button
          size="sm"
          className="mt-1 gap-1.5"
          disabled={disabled}
          onClick={() => onStart(scenario.scenario_id)}
        >
          <MessageCircle size={14} />
          Start Practice
        </Button>
      </CardContent>
    </Card>
  );
}
