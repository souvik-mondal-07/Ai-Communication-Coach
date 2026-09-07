import { BookOpen, Target } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { TopicSummary } from "@/features/cybersecurity/cybersecurityTypes";
import { DIFFICULTY_LABELS } from "@/features/cybersecurity/cybersecurityTypes";

interface TopicCardProps {
  topic: TopicSummary;
  onOpen: (slug: string) => void;
  onPractice: (slug: string) => void;
  practiceDisabled?: boolean;
}

const DIFFICULTY_STYLES: Record<string, string> = {
  beginner: "text-signal border-signal/30 bg-signal/10",
  intermediate: "text-warn border-warn/30 bg-warn/10",
  advanced: "text-danger border-danger/30 bg-danger/10",
};

export function TopicCard({ topic, onOpen, onPractice, practiceDisabled }: TopicCardProps) {
  return (
    <Card className="flex flex-col">
      <CardContent className="flex flex-1 flex-col gap-3 py-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-sm font-semibold text-text-primary">{topic.title}</h3>
          <span
            className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-medium ${
              DIFFICULTY_STYLES[topic.difficulty] ?? DIFFICULTY_STYLES.intermediate
            }`}
          >
            {DIFFICULTY_LABELS[topic.difficulty]}
          </span>
        </div>
        <p className="text-xs text-text-muted">{topic.category}</p>
        <p className="flex-1 text-sm text-text-secondary">{topic.description}</p>
        <div className="mt-1 flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            className="flex-1 gap-1.5"
            onClick={() => onOpen(topic.slug)}
          >
            <BookOpen size={14} />
            Start Learning
          </Button>
          <Button
            variant="primary"
            size="sm"
            className="flex-1 gap-1.5"
            disabled={!topic.practice_enabled || practiceDisabled}
            onClick={() => onPractice(topic.slug)}
          >
            <Target size={14} />
            Practice
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
