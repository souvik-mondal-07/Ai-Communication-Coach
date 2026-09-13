import { api } from "@/services/api";
import type {
  Category,
  Difficulty,
  Evaluation,
  Mode,
  ScenarioDetail,
  ScenarioSummary,
  SessionDetail,
  SessionSummary,
} from "@/features/communication/communicationTypes";

/**
 * Client for the communication coach endpoints. Talks only to FastAPI
 * (`/api/v1/communication/...`) — roleplay chat and evaluation happen
 * server-side via Gemini; this file never calls an AI provider directly.
 */

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export async function getScenarios(filters?: {
  category?: Category;
  mode?: Mode;
  difficulty?: Difficulty;
}): Promise<ScenarioSummary[]> {
  const { data } = await api.get<ApiEnvelope<{ scenarios: ScenarioSummary[] }>>(
    "/communication/scenarios",
    { params: filters }
  );
  return data.data.scenarios;
}

export async function getScenario(slug: string): Promise<ScenarioDetail> {
  const { data } = await api.get<ApiEnvelope<{ scenario: ScenarioDetail }>>(
    `/communication/scenarios/${encodeURIComponent(slug)}`
  );
  return data.data.scenario;
}

export async function startSession(
  scenarioId: string,
  difficulty?: Difficulty
): Promise<{ session_id: string; scenario: ScenarioDetail; status: string }> {
  const { data } = await api.post<
    ApiEnvelope<{ session_id: string; scenario: ScenarioDetail; status: string }>
  >("/communication/sessions", { scenario_id: scenarioId, difficulty });
  return data.data;
}

export async function sendMessage(
  sessionId: string,
  message: string
): Promise<{ reply: string; session_id: string; message_id: string }> {
  const { data } = await api.post<
    ApiEnvelope<{ reply: string; session_id: string; message_id: string }>
  >(`/communication/sessions/${encodeURIComponent(sessionId)}/message`, { message });
  return data.data;
}

export async function completeSession(
  sessionId: string
): Promise<{ session_id: string; evaluation: Evaluation }> {
  const { data } = await api.post<ApiEnvelope<{ session_id: string; evaluation: Evaluation }>>(
    `/communication/sessions/${encodeURIComponent(sessionId)}/complete`
  );
  return data.data;
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  const { data } = await api.get<ApiEnvelope<SessionDetail>>(
    `/communication/sessions/${encodeURIComponent(sessionId)}`
  );
  return data.data;
}

export async function getSessions(params?: {
  page?: number;
  limit?: number;
}): Promise<{ sessions: SessionSummary[]; page: number; limit: number; total: number }> {
  const { data } = await api.get<
    ApiEnvelope<{ sessions: SessionSummary[]; page: number; limit: number; total: number }>
  >("/communication/sessions", { params });
  return data.data;
}
