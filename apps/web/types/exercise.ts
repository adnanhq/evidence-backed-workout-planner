import type { EvidenceTier } from "./protocol";

export interface ExerciseSummary {
  exerciseId: string;
  name: string;
  primaryMuscles: string[];
  secondaryMuscles: string[];
  equipment: string[];
  difficulty: string | null;
  mechanic: string | null;
  force: string | null;
  category: string | null;
  trainingGoals: string[];
  evidenceCount: number;
  confidenceLevel: string | null;
  confidenceScore: number | null;
  bestTier: EvidenceTier | null;
  thumbnail: string | null;
  gif: string | null;
}

export interface ExerciseStudy {
  pmid: string | null;
  title: string | null;
  year: number | null;
  tier: EvidenceTier;
  trustLabel: string;
  snippet: string | null;
  url: string | null;
  qualityScore: number | null;
  matchedAlias: string | null;
  participantCount: number | null;
  measurementMethod: string[];
}

export interface GoalProfile {
  score: number;
  recommended: boolean;
  rationale: string[];
}

export interface ExercisesResponse {
  total: number;
  page: number;
  pageSize: number;
  items: ExerciseSummary[];
}

export interface ExerciseDetail extends ExerciseSummary {
  aliases: string[];
  images: string[];
  instructions: string[];
  goalProfiles: Record<string, GoalProfile>;
  jointStress: {
    profile?: Record<string, { score: number; label: string }>;
    high_stress_joints?: string[];
  };
  rankingScores: Record<string, number>;
  muscleGroupRankings: Record<string, Record<string, { rank: number; out_of: number }>>;
  evidence: {
    confidenceScore: number | null;
    confidenceLevel: string | null;
    directEvidenceCount: number;
    tierCounts: Record<string, number>;
    fallbackBasis: string[];
    studies: ExerciseStudy[];
    comparativeFindings: unknown[];
  };
}

export interface EvidenceDoc {
  pmid: string | null;
  docId: string | null;
  title: string | null;
  abstract: string | null;
  authors: string[];
  journal: string | null;
  year: number | null;
  publicationTypes: string[];
  doi: string | null;
  tier: EvidenceTier;
  topicClusters: string[];
  participantCount: number | null;
  measurementModalities: string[];
  manualReviewRequired: boolean;
  url: string | null;
}
