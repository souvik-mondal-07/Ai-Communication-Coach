import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TopicCard } from "@/features/cybersecurity/TopicCard";
import { TopicFilters } from "@/features/cybersecurity/TopicFilters";
import type { Difficulty, TopicSummary } from "@/features/cybersecurity/cybersecurityTypes";
import { getTopics } from "@/services/cybersecurityService";
import { usePracticeStore } from "@/store/practiceStore";
import { getApiErrorMessage } from "@/utils/apiError";

export default function Cybersecurity() {
  const navigate = useNavigate();
  const startPractice = usePracticeStore((s) => s.start);

  const [topics, setTopics] = useState<TopicSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string | "all">("all");
  const [difficulty, setDifficulty] = useState<Difficulty | "all">("all");
  const [startingSlug, setStartingSlug] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    getTopics()
      .then((result) => {
        if (!cancelled) setTopics(result);
      })
      .catch((err) => {
        if (!cancelled) setError(getApiErrorMessage(err, "Unable to load cybersecurity topics."));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const categories = useMemo(
    () => Array.from(new Set(topics.map((t) => t.category))).sort(),
    [topics]
  );

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return topics.filter((topic) => {
      if (category !== "all" && topic.category !== category) return false;
      if (difficulty !== "all" && topic.difficulty !== difficulty) return false;
      if (query && !topic.title.toLowerCase().includes(query) && !topic.description.toLowerCase().includes(query)) {
        return false;
      }
      return true;
    });
  }, [topics, search, category, difficulty]);

  const grouped = useMemo(() => {
    const map = new Map<string, TopicSummary[]>();
    for (const topic of filtered) {
      const list = map.get(topic.category) ?? [];
      list.push(topic);
      map.set(topic.category, list);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [filtered]);

  async function handlePractice(slug: string) {
    setStartingSlug(slug);
    try {
      const sessionId = await startPractice(slug);
      navigate(`/cybersecurity/practice/${sessionId}`);
    } catch {
      // The practice store already records the error; surface it inline.
      setError("Unable to generate practice questions. Please try again.");
    } finally {
      setStartingSlug(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl font-semibold text-text-primary">
          Cybersecurity Learning
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Browse topics, learn the concepts, then practice what you've learned.
        </p>
      </div>

      <TopicFilters
        search={search}
        onSearchChange={setSearch}
        category={category}
        onCategoryChange={setCategory}
        categories={categories}
        difficulty={difficulty}
        onDifficultyChange={setDifficulty}
      />

      {error && (
        <div className="rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      {isLoading ? (
        <p className="py-10 text-center text-sm text-text-muted">Loading topics…</p>
      ) : grouped.length === 0 ? (
        <p className="py-10 text-center text-sm text-text-muted">No topics match your filters.</p>
      ) : (
        <div className="space-y-8">
          {grouped.map(([categoryName, categoryTopics]) => (
            <section key={categoryName}>
              <h2 className="mb-3 text-sm font-semibold text-text-primary">{categoryName}</h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {categoryTopics.map((topic) => (
                  <TopicCard
                    key={topic.slug}
                    topic={topic}
                    onOpen={(slug) => navigate(`/cybersecurity/${slug}`)}
                    onPractice={handlePractice}
                    practiceDisabled={startingSlug === topic.slug}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
