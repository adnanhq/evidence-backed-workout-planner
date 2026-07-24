export type Goal = "hypertrophy" | "strength";
export type Experience = "beginner" | "intermediate" | "advanced";
export type SplitTemplate =
  | "auto"
  | "full_body"
  | "push_pull"
  | "push_pull_legs"
  | "upper_lower";
export type Joint =
  | "neck"
  | "shoulder"
  | "elbow"
  | "wrist"
  | "spine"
  | "hip"
  | "knee"
  | "ankle";
export type EvidenceTier =
  | "meta_analysis"
  | "rct"
  | "systematic_review"
  | "controlled_trial"
  | "observational"
  | "narrative_review"
  | "other";
export type TrustLabel = "standard" | "lower-trust";

export interface EvidenceItem {
  pmid: string | null;
  title: string | null;
  year: number | null;
  tier: EvidenceTier;
  trustLabel: TrustLabel;
  snippet: string | null;
  url: string | null;
  manualReviewRequired?: boolean;
}

export interface Prescription {
  sets: string | null;
  reps: string | null;
  rest: string | null;
  display: string | null;
}

export interface ProtocolExercise {
  exerciseId: string;
  name: string;
  targetMuscle: string;
  targetLabel: string;
  rankDisplay: string | null;
  selectionReason: string | null;
  lowerTrustEvidence: boolean;
  thumbnail: string | null;
  prescription: Prescription;
  referencePmids: string[];
  referenceEvidence: EvidenceItem[];
}

export interface ProtocolSession {
  sessionNumber: number;
  splitLabel: string;
  focus: string | null;
  targetMuscles: string[];
  exercises: ProtocolExercise[];
}

export interface GenerateRequestEcho {
  goal: Goal;
  muscles: string[];
  sessions: number;
  sessionMinutes: number;
  exercisesPerSession: number | null;
  equipment: string[];
  experience: Experience;
  avoidJoints: string[];
  notes: string;
  splitTemplate: SplitTemplate;
}

export interface GenerateResponse {
  request: GenerateRequestEcho;
  splitSummary: string | null;
  splitTemplate: string | null;
  planner: string | null;
  plannerModel: string | null;
  usedFallback: boolean;
  exercisesPerSession: number | null;
  warnings: string[];
  sessions: ProtocolSession[];
  evidenceAppendix: EvidenceItem[];
  markdown: string;
}

export interface GenerateRequest {
  goal: Goal;
  muscles: string[];
  sessions: number;
  sessionMinutes: number;
  exercisesPerSession?: number | null;
  equipment: string[];
  experience: Experience;
  avoidJoints: Joint[];
  notes?: string;
  splitTemplate: SplitTemplate;
  model?: string | null;
}

export interface Taxonomies {
  goals: string[];
  muscleGroups: string[];
  equipment: string[];
  difficulty: string[];
  joints: string[];
  splitTemplates: string[];
  experienceLevels: string[];
  displayLabels?: { muscles: Record<string, string> };
  equipmentPresets?: Record<string, string[]>;
}
