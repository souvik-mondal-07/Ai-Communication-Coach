import { ArrowLeft, Target } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { TopicDetail as TopicDetailType } from "@/features/cybersecurity/cybersecurityTypes";
import { DIFFICULTY_LABELS } from "@/features/cybersecurity/cybersecurityTypes";

interface TopicDetailProps {
  topic: TopicDetailType;
  onBack: () => void;
  onStartPractice: () => void;
  practiceDisabled?: boolean;
}

export function TopicDetail({ topic, onBack, onStartPractice, practiceDisabled }: TopicDetailProps) {
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <button
        type="button"
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary"
      >
        <ArrowLeft size={15} />
        Back to topics
      </button>

      <div>
        <p className="text-xs font-medium text-signal">{topic.category}</p>
        <h1 className="mt-1 font-display text-2xl font-semibold text-text-primary">
          {topic.title}
        </h1>
        <p className="mt-1 text-sm text-text-muted">
          Difficulty: {DIFFICULTY_LABELS[topic.difficulty]}
        </p>
      </div>

      <Card>
        <CardContent className="space-y-5 py-5">
          <section>
            <h2 className="mb-1.5 text-sm font-semibold text-text-primary">Overview</h2>
            <p className="text-sm leading-relaxed text-text-secondary">{topic.description}</p>
          </section>

          {topic.learning_objectives.length > 0 && (
            <section>
              <h2 className="mb-1.5 text-sm font-semibold text-text-primary">
                Learning Objectives
              </h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-text-secondary">
                {topic.learning_objectives.map((objective) => (
                  <li key={objective}>{objective}</li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h2 className="mb-1.5 text-sm font-semibold text-text-primary">How It Works</h2>
            <div className="prose-mentor text-sm leading-relaxed text-text-secondary">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  ul: ({ children }) => (
                    <ul className="my-1.5 list-disc space-y-1 pl-5">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="my-1.5 list-decimal space-y-1 pl-5">{children}</ol>
                  ),
                  code: ({ children }) => (
                    <code className="rounded bg-surface-raised px-1 py-0.5 text-[13px]">
                      {children}
                    </code>
                  ),
                }}
              >
                {topic.content}
              </ReactMarkdown>
            </div>
          </section>

          {topic.examples.length > 0 && (
            <section>
              <h2 className="mb-1.5 text-sm font-semibold text-text-primary">Example</h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-text-secondary">
                {topic.examples.map((example) => (
                  <li key={example}>{example}</li>
                ))}
              </ul>
            </section>
          )}

          {topic.key_points.length > 0 && (
            <section>
              <h2 className="mb-1.5 text-sm font-semibold text-text-primary">Key Points</h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-text-secondary">
                {topic.key_points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </section>
          )}
        </CardContent>
      </Card>

      <Button
        className="w-full gap-1.5 sm:w-auto"
        disabled={!topic.practice_enabled || practiceDisabled}
        onClick={onStartPractice}
      >
        <Target size={15} />
        Start Practice
      </Button>
    </div>
  );
}
