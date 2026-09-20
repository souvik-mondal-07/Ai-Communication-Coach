import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ScenarioCard } from "@/features/communication/ScenarioCard";
import { ScenarioFilters } from "@/features/communication/ScenarioFilters";
import { InputModeToggle } from "@/features/voice/InputModeToggle";
import type { InputMode } from "@/features/voice/voiceTypes";
import { isVoiceSupported } from "@/hooks/useVoice";
import type {
  Category,
  Difficulty,
  Mode,
  ScenarioSummary,
} from "@/features/communication/communicationTypes";
import * as communicationService from "@/services/communicationService";
import { getApiErrorMessage } from "@/utils/apiError";

export default function Communication() {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<Category | "all">("all");
  const [mode, setMode] = useState<Mode | "all">("all");
  const [difficulty, setDifficulty] = useState<Difficulty | "all">("all");
  const [startingId, setStartingId] = useState<string | null>(null);
  const voiceSupported = isVoiceSupported();
  const [inputMode, setInputMode] = useState<InputMode>("text");

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    communicationService
      .getScenarios()
      .then((result) => {
        if (!cancelled) setScenarios(result);
      })
      .catch((err) => {
        if (!cancelled) setError(getApiErrorMessage(err, "Unable to load scenarios."));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = scenarios.filter((scenario) => {
    if (category !== "all" && scenario.category !== category) return false;
    if (mode !== "all" && scenario.mode !== mode) return false;
    if (difficulty !== "all" && scenario.difficulty !== difficulty) return false;
    return true;
  });

  async function handleStart(scenarioId: string) {
    setStartingId(scenarioId);
    try {
      const result = await communicationService.startSession(scenarioId);
      navigate(
        inputMode === "voice"
          ? `/communication/${result.session_id}?input=voice`
          : `/communication/${result.session_id}`
      );
    } catch (err) {
      setError(getApiErrorMessage(err, "Unable to start this practice session."));
    } finally {
      setStartingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl font-semibold text-text-primary">
          Real-Life Communication Coach
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Practice realistic conversations by typing or speaking, then get concrete feedback on
          your communication.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-text-secondary">Practice with:</span>
        <InputModeToggle value={inputMode} onChange={setInputMode} voiceSupported={voiceSupported} />
        {!voiceSupported && (
          <span className="text-xs text-text-muted">
            Voice needs a browser with microphone recording support and a secure (https/localhost) connection.
          </span>
        )}
      </div>

      <ScenarioFilters
        category={category}
        onCategoryChange={setCategory}
        mode={mode}
        onModeChange={setMode}
        difficulty={difficulty}
        onDifficultyChange={setDifficulty}
      />

      {error && (
        <div className="rounded-[var(--radius-panel)] border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      {isLoading ? (
        <p className="py-10 text-center text-sm text-text-muted">Loading scenarios…</p>
      ) : filtered.length === 0 ? (
        <p className="py-10 text-center text-sm text-text-muted">No scenarios match your filters.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((scenario) => (
            <ScenarioCard
              key={scenario.scenario_id}
              scenario={scenario}
              onStart={handleStart}
              disabled={startingId === scenario.scenario_id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
