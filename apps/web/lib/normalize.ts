import { pubmedUrl } from "./evidence";
import type {
  EvidenceItem,
  EvidenceTier,
  GenerateResponse,
  Prescription,
  ProtocolExercise,
  ProtocolSession,
  TrustLabel,
} from "@/types/protocol";

/* The single defensive boundary between the engine's JSON and the UI.
   The API already returns camelCase with derived URLs, but we backfill
   url / tier / trustLabel / year so the UI never breaks on shape drift. */

type Raw = Record<string, unknown>;

function str(v: unknown): string | null {
  return v == null ? null : String(v);
}

export function normalizeEvidence(raw: Raw): EvidenceItem {
  const pmid = raw.pmid != null ? String(raw.pmid) : null;
  const tier = (raw.tier as EvidenceTier) ?? "other";
  const trustLabel =
    (raw.trustLabel as TrustLabel) ??
    (raw.lowerTrustEvidence ? "lower-trust" : "standard");
  return {
    pmid,
    title: str(raw.title),
    year: (raw.year as number) ?? (raw.publicationYear as number) ?? null,
    tier,
    trustLabel,
    snippet: str(raw.snippet),
    url: (raw.url as string) ?? pubmedUrl(pmid),
    manualReviewRequired: Boolean(raw.manualReviewRequired),
  };
}

function normalizePrescription(raw: Raw | undefined): Prescription {
  const p = raw ?? {};
  return {
    sets: str(p.sets),
    reps: str(p.reps),
    rest: str(p.rest),
    display: str(p.display),
  };
}

function normalizeExercise(raw: Raw): ProtocolExercise {
  return {
    exerciseId: String(raw.exerciseId ?? ""),
    name: String(raw.name ?? "Exercise"),
    targetMuscle: String(raw.targetMuscle ?? ""),
    targetLabel: String(raw.targetLabel ?? raw.targetMuscle ?? ""),
    rankDisplay: str(raw.rankDisplay),
    selectionReason: str(raw.selectionReason),
    lowerTrustEvidence: Boolean(raw.lowerTrustEvidence),
    thumbnail: str(raw.thumbnail),
    prescription: normalizePrescription(raw.prescription as Raw),
    referencePmids: ((raw.referencePmids as unknown[]) ?? []).map(String),
    referenceEvidence: ((raw.referenceEvidence as Raw[]) ?? []).map(normalizeEvidence),
  };
}

function normalizeSession(raw: Raw): ProtocolSession {
  return {
    sessionNumber: Number(raw.sessionNumber ?? 0),
    splitLabel: String(raw.splitLabel ?? "Session"),
    focus: str(raw.focus),
    targetMuscles: ((raw.targetMuscles as unknown[]) ?? []).map(String),
    exercises: ((raw.exercises as Raw[]) ?? []).map(normalizeExercise),
  };
}

export function normalizeResponse(input: unknown): GenerateResponse {
  const raw = (input ?? {}) as Raw;
  const request = (raw.request ?? {}) as Raw;
  return {
    request: {
      goal: (request.goal as GenerateResponse["request"]["goal"]) ?? "hypertrophy",
      muscles: ((request.muscles as unknown[]) ?? []).map(String),
      sessions: Number(request.sessions ?? 0),
      sessionMinutes: Number(request.sessionMinutes ?? 0),
      exercisesPerSession: (request.exercisesPerSession as number) ?? null,
      equipment: ((request.equipment as unknown[]) ?? []).map(String),
      experience:
        (request.experience as GenerateResponse["request"]["experience"]) ??
        "intermediate",
      avoidJoints: ((request.avoidJoints as unknown[]) ?? []).map(String),
      notes: String(request.notes ?? ""),
      splitTemplate:
        (request.splitTemplate as GenerateResponse["request"]["splitTemplate"]) ??
        "auto",
    },
    splitSummary: str(raw.splitSummary),
    splitTemplate: str(raw.splitTemplate),
    planner: str(raw.planner),
    plannerModel: str(raw.plannerModel),
    usedFallback: Boolean(raw.usedFallback),
    exercisesPerSession: (raw.exercisesPerSession as number) ?? null,
    warnings: ((raw.warnings as unknown[]) ?? []).map(String),
    sessions: ((raw.sessions as Raw[]) ?? []).map(normalizeSession),
    evidenceAppendix: ((raw.evidenceAppendix as Raw[]) ?? []).map(normalizeEvidence),
    markdown: String(raw.markdown ?? ""),
  };
}
