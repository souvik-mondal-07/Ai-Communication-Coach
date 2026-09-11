import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  CATEGORY_LABELS,
  DIFFICULTY_LABELS,
  PLATFORMS,
  type ChallengeCategory,
  type CtfDifficulty,
  type Platform,
} from "@/features/cybersecurity/ctf/ctfTypes";

interface CtfSessionFormProps {
  onSubmit: (payload: {
    platform: Platform;
    category: ChallengeCategory;
    difficulty: CtfDifficulty;
    title: string;
    description: string;
    user_notes: string;
  }) => Promise<void>;
  onCancel: () => void;
}

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS) as [ChallengeCategory, string][];

export function CtfSessionForm({ onSubmit, onCancel }: CtfSessionFormProps) {
  const [platform, setPlatform] = useState<Platform>("Hack The Box");
  const [category, setCategory] = useState<ChallengeCategory>("web_security");
  const [difficulty, setDifficulty] = useState<CtfDifficulty>("easy");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [userNotes, setUserNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!title.trim() || !description.trim()) {
      setError("Title and description are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await onSubmit({
        platform,
        category,
        difficulty,
        title: title.trim(),
        description: description.trim(),
        user_notes: userNotes.trim(),
      });
    } catch {
      setError("Unable to start the session. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-text-secondary">Platform</span>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value as Platform)}
            className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary"
          >
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-text-secondary">Category</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as ChallengeCategory)}
            className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary"
          >
            {CATEGORY_OPTIONS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1.5 block text-xs font-medium text-text-secondary">Difficulty</span>
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value as CtfDifficulty)}
            className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary"
          >
            {Object.entries(DIFFICULTY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="block">
        <span className="mb-1.5 block text-xs font-medium text-text-secondary">
          Challenge Title
        </span>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Login Bypass"
          className="w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
        />
      </label>

      <label className="block">
        <span className="mb-1.5 block text-xs font-medium text-text-secondary">
          Challenge Description
        </span>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          placeholder="What have you found so far? e.g. I found port 80 open and the website has a login page."
          className="w-full resize-none rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
        />
      </label>

      <label className="block">
        <span className="mb-1.5 block text-xs font-medium text-text-secondary">
          What I Tried (optional)
        </span>
        <textarea
          value={userNotes}
          onChange={(e) => setUserNotes(e.target.value)}
          rows={2}
          placeholder="e.g. I checked the page source and found..."
          className="w-full resize-none rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
        />
      </label>

      {error && <p className="text-sm text-danger">{error}</p>}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Starting…" : "Start Mentor Session"}
        </Button>
      </div>
    </form>
  );
}
