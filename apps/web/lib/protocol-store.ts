import type {
  GenerateRequest,
  GenerateRequestEcho,
  GenerateResponse,
  Joint,
} from "@/types/protocol";

// A generated protocol lives only in the client (no DB). We hand it off from the
// builder to the dedicated /protocol page via sessionStorage (durable across an
// in-tab refresh) plus the React Query cache (in-memory fast path). All access is
// guarded for SSR safety.
export const PROTOCOL_STORAGE_KEY = "protocol:last";
export const PROTOCOL_QUERY_KEY = ["protocol", "last"] as const;

export interface StashedProtocol {
  request: GenerateRequest;
  response: GenerateResponse;
  savedAt: number;
}

export function saveProtocol(
  request: GenerateRequest,
  response: GenerateResponse,
): void {
  if (typeof window === "undefined") return;
  try {
    const payload: StashedProtocol = { request, response, savedAt: Date.now() };
    window.sessionStorage.setItem(PROTOCOL_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // sessionStorage may be unavailable (quota / private mode). The in-tab query
    // cache still carries the result for the immediate navigation.
  }
}

export function loadProtocol(): StashedProtocol | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(PROTOCOL_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StashedProtocol;
    if (!parsed?.response?.sessions) return null; // guard against shape drift
    return parsed;
  } catch {
    return null;
  }
}

export function clearProtocol(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(PROTOCOL_STORAGE_KEY);
  } catch {
    // ignore
  }
}

// Normalize a stored request (or the echoed request on a response) back to the
// builder's form-shaped GenerateRequest, filling defaults.
export function echoToRequest(
  req: GenerateRequest | GenerateRequestEcho,
): GenerateRequest {
  return {
    goal: req.goal,
    muscles: req.muscles ?? [],
    sessions: req.sessions,
    sessionMinutes: req.sessionMinutes,
    exercisesPerSession: req.exercisesPerSession ?? null,
    equipment: req.equipment ?? [],
    experience: req.experience,
    avoidJoints: (req.avoidJoints ?? []) as Joint[],
    notes: req.notes ?? "",
    splitTemplate: req.splitTemplate,
  };
}
