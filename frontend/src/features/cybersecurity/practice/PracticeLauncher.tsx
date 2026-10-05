import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  PRACTICE_DIFFICULTY_LABELS,
  QUESTION_TYPE_LABELS,
  type PracticeConfig,
  type PracticeDifficulty,
  type PracticeMode,
  type QuestionTypeChoice,
} from "@/features/cybersecurity/cybersecurityTypes";
import { getPracticeConfig } from "@/services/cybersecurityService";
import { usePracticeStore } from "@/store/practiceStore";
import { getApiErrorMessage } from "@/utils/apiError";

const fieldClass =
  "w-full rounded-[var(--radius-panel)] border border-border bg-surface-raised px-3 py-2 text-sm text-text-primary disabled:opacity-60";

export function PracticeLauncher() {
  const navigate = useNavigate();
  const startSession = usePracticeStore((s) => s.startSession);

  const [config, setConfig] = useState<PracticeConfig | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mode, setMode] = useState<PracticeMode>("personalized");
  const [category, setCategory] = useState("");
  const [difficulty, setDifficulty] = useState<PracticeDifficulty>("adaptive");
  const [questionType, setQuestionType] = useState<QuestionTypeChoice>("mixed");
  const [count, setCount] = useState(5);
  const [timed, setTimed] = useState(false);
  const [minutes, setMinutes] = useState(15);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  // Opening the page only reads the topic catalogue; no AI call happens until "Start Practice".
  useEffect(() => {
    let cancelled = false;
    getPracticeConfig()
      .then((c) => {
        if (cancelled) return;
        setConfig(c);
        setCount(c.limits.default_questions);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(getApiErrorMessage(err, "Unable to load practice options."));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const modeInfo = config?.modes.find((m) => m.id === mode);
  const categoryInfo = config?.categories.find((c) => c.category === category);

  const typeOptions = useMemo<QuestionTypeChoice[]>(() => {
    if (!config) return ["mixed"];
    if (!categoryInfo) return config.question_types;
    return ["mixed", ...categoryInfo.question_types];
  }, [config, categoryInfo]);

  const needsCategory = modeInfo?.category === "required";
  const showCategory = modeInfo !== undefined && modeInfo.category !== "none";
  const fixedType = modeInfo?.fixed_type ?? null;
  const canStart = !!config && !isStarting && (!needsCategory || category !== "");

  function pickMode(next: PracticeMode) {
    setMode(next);
    setStartError(null);
    if (config?.modes.find((m) => m.id === next)?.category === "none") setCategory("");
  }

  function pickCategory(next: string) {
    setCategory(next);
    // Drop a type this category can't do (e.g. command tasks for Cryptography).
    const info = config?.categories.find((c) => c.category === next);
    if (info && questionType !== "mixed" && !info.question_types.includes(questionType)) setQuestionType("mixed");
  }

  async function handleStart() {
    if (!config || !canStart) return;
    setIsStarting(true);
    setStartError(null);
    try {
      const id = await startSession({
        mode,
        category: showCategory ? category || null : null,
        difficulty,
        questionType: fixedType ?? questionType,
        questionCount: count,
        timeLimitMinutes: timed ? minutes : null,
      });
      navigate(`/cybersecurity/practice/${id}`);
    } catch (err) {
      setStartError(getApiErrorMessage(err, "Unable to start practice. Please try again."));
    } finally {
      setIsStarting(false);
    }
  }

  if (loadError) {
    return <p className="rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">{loadError}</p>;
  }
  if (!config) {
    return <p className="py-10 text-center text-sm text-text-muted">Loading practice options…</p>;
  }

  return (
    <Card>
      <CardContent className="space-y-5 py-5">
        <div role="tablist" aria-label="Practice mode" className="flex flex-wrap gap-2">
          {config.modes.map((m) => (
            <button
              key={m.id}
              type="button"
              role="tab"
              aria-selected={mode === m.id}
              onClick={() => pickMode(m.id)}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                mode === m.id
                  ? "border-signal bg-signal/10 text-signal"
                  : "border-border text-text-secondary hover:border-border-strong"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        {modeInfo && <p className="text-sm text-text-secondary">{modeInfo.description}</p>}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {showCategory && (
            <label className="space-y-1 text-xs text-text-secondary">
              Topic{needsCategory ? "" : " (optional)"}
              <select value={category} onChange={(e) => pickCategory(e.target.value)} className={fieldClass}>
                <option value="">{needsCategory ? "Choose a category…" : "Let the engine choose"}</option>
                {config.categories.map((c) => (
                  <option key={c.category} value={c.category}>
                    {c.category}
                  </option>
                ))}
              </select>
            </label>
          )}

          <label className="space-y-1 text-xs text-text-secondary">
            Difficulty
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as PracticeDifficulty)}
              className={fieldClass}
            >
              {config.difficulties.map((d) => (
                <option key={d} value={d}>
                  {PRACTICE_DIFFICULTY_LABELS[d]}
                  {d === "adaptive" ? " (based on your results)" : ""}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1 text-xs text-text-secondary">
            Question type
            <select
              value={fixedType ?? questionType}
              disabled={fixedType !== null}
              onChange={(e) => setQuestionType(e.target.value as QuestionTypeChoice)}
              className={fieldClass}
            >
              {(fixedType ? [fixedType] : typeOptions).map((t) => (
                <option key={t} value={t}>
                  {QUESTION_TYPE_LABELS[t]}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1 text-xs text-text-secondary">
            Questions: {count}
            <input
              type="range"
              min={config.limits.min_questions}
              max={config.limits.max_questions}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="w-full accent-[var(--color-signal)]"
            />
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs text-text-secondary">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={timed} onChange={(e) => setTimed(e.target.checked)} />
            Timed session
          </label>
          {timed && (
            <label className="flex items-center gap-2">
              <input
                type="number"
                min={config.limits.min_time_limit_minutes}
                max={config.limits.max_time_limit_minutes}
                value={minutes}
                onChange={(e) =>
                  setMinutes(
                    Math.min(
                      config.limits.max_time_limit_minutes,
                      Math.max(config.limits.min_time_limit_minutes, Number(e.target.value) || 0)
                    )
                  )
                }
                className={`${fieldClass} w-20`}
                aria-label="Minutes"
              />
              minutes
            </label>
          )}
        </div>

        {startError && (
          <p className="rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
            {startError}
          </p>
        )}

        <div className="flex justify-center">
          <Button size="lg" disabled={!canStart} onClick={() => void handleStart()}>
            {isStarting ? "Preparing your first question…" : "Start Practice"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
