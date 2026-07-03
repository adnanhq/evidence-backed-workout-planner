import type {
  GenerateRequest,
  GenerateResponse,
  Taxonomies,
} from "@/types/protocol";
import type {
  EvidenceDoc,
  ExerciseDetail,
  ExercisesResponse,
} from "@/types/exercise";
import { normalizeResponse } from "./normalize";

export const ENGINE_URL =
  process.env.NEXT_PUBLIC_ENGINE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

interface FetchOpts extends RequestInit {
  timeoutMs?: number;
}

async function fetchJson<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const { timeoutMs = 25_000, headers, ...rest } = opts;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${ENGINE_URL}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: { "content-type": "application/json", ...headers },
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) {
      const detail = data?.detail ?? data?.message ?? `Request failed (${res.status})`;
      throw new ApiError(
        res.status,
        typeof detail === "string" ? detail : JSON.stringify(detail),
      );
    }
    return data as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if ((err as Error)?.name === "AbortError") {
      throw new ApiError(0, "The request timed out. The model may be busy — try again.");
    }
    throw new ApiError(
      0,
      "Couldn't reach the protocol engine. Make sure it's running on " + ENGINE_URL,
    );
  } finally {
    clearTimeout(timer);
  }
}

export async function generateProtocol(
  req: GenerateRequest,
): Promise<GenerateResponse> {
  const raw = await fetchJson<unknown>("/api/protocol/generate", {
    method: "POST",
    body: JSON.stringify(req),
    // The configured Gemini model can take ~1–2 minutes; allow plenty of headroom.
    timeoutMs: 220_000,
  });
  return normalizeResponse(raw);
}

export function getTaxonomies(): Promise<Taxonomies> {
  return fetchJson<Taxonomies>("/api/taxonomies");
}

export interface ExerciseQuery {
  q?: string;
  muscle?: string;
  equipment?: string;
  difficulty?: string;
  goal?: string;
  page?: number;
  pageSize?: number;
}

export function getExercises(params: ExerciseQuery): Promise<ExercisesResponse> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.muscle) qs.set("muscle", params.muscle);
  if (params.equipment) qs.set("equipment", params.equipment);
  if (params.difficulty) qs.set("difficulty", params.difficulty);
  if (params.goal) qs.set("goal", params.goal);
  qs.set("page", String(params.page ?? 1));
  qs.set("page_size", String(params.pageSize ?? 24));
  return fetchJson<ExercisesResponse>(`/api/exercises?${qs.toString()}`);
}

export function getExercise(id: string): Promise<ExerciseDetail> {
  return fetchJson<ExerciseDetail>(`/api/exercises/${encodeURIComponent(id)}`);
}

export function getEvidence(pmid: string): Promise<EvidenceDoc> {
  return fetchJson<EvidenceDoc>(`/api/evidence/${encodeURIComponent(pmid)}`);
}
