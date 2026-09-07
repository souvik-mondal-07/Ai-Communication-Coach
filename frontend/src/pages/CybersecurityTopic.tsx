import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { TopicDetail } from "@/features/cybersecurity/TopicDetail";
import type { TopicDetail as TopicDetailType } from "@/features/cybersecurity/cybersecurityTypes";
import { getTopic } from "@/services/cybersecurityService";
import { usePracticeStore } from "@/store/practiceStore";
import { getApiErrorMessage } from "@/utils/apiError";

export default function CybersecurityTopic() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const startPractice = usePracticeStore((s) => s.start);

  const [topic, setTopic] = useState<TopicDetailType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isStartingPractice, setIsStartingPractice] = useState(false);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    getTopic(slug)
      .then((result) => {
        if (!cancelled) setTopic(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(getApiErrorMessage(err, "Unable to load this topic."));
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  async function handleStartPractice() {
    if (!slug) return;
    setIsStartingPractice(true);
    try {
      const sessionId = await startPractice(slug);
      navigate(`/cybersecurity/practice/${sessionId}`);
    } catch {
      setError("Unable to generate practice questions. Please try again.");
    } finally {
      setIsStartingPractice(false);
    }
  }

  if (isLoading) {
    return <p className="py-16 text-center text-sm text-text-muted">Loading topic…</p>;
  }

  if (error || !topic) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <p className="text-sm text-danger">{error ?? "Topic not found."}</p>
        <button
          type="button"
          onClick={() => navigate("/cybersecurity")}
          className="mt-4 text-sm text-link hover:underline"
        >
          Back to topics
        </button>
      </div>
    );
  }

  return (
    <TopicDetail
      topic={topic}
      onBack={() => navigate("/cybersecurity")}
      onStartPractice={() => void handleStartPractice()}
      practiceDisabled={isStartingPractice}
    />
  );
}
