import type { Taxonomies } from "@/types/protocol";

/**
 * Local fallback so the builder is usable even before the engine's
 * /api/taxonomies endpoint responds (seeded as TanStack Query initialData).
 * Mirrors the catalog taxonomies exactly.
 */
export const FALLBACK_TAXONOMIES: Taxonomies = {
  goals: ["hypertrophy", "strength"],
  // Primary-mover muscles only, mirroring /api/taxonomies ("neck" is excluded —
  // no exercise trains it as a primary mover, so filtering on it returns nothing).
  muscleGroups: [
    "abs",
    "biceps",
    "calves",
    "chest",
    "delts",
    "forearms",
    "glutes",
    "hamstrings",
    "hip_abductors",
    "hip_adductors",
    "lats",
    "mid_back",
    "quads",
    "spinal_erectors",
    "traps",
    "triceps",
  ],
  equipment: [
    "barbell",
    "bodyweight",
    "cable",
    "dumbbell",
    "ez_bar",
    "foam_roller",
    "kettlebell",
    "machine",
    "medicine_ball",
    "other",
    "resistance_band",
    "stability_ball",
    "unknown",
  ],
  difficulty: ["beginner", "intermediate", "advanced", "unknown"],
  joints: ["neck", "shoulder", "elbow", "wrist", "spine", "hip", "knee", "ankle"],
  splitTemplates: ["auto", "full_body", "push_pull", "push_pull_legs", "upper_lower"],
  experienceLevels: ["beginner", "intermediate", "advanced"],
};

export const STATS = {
  exercises: 1324,
  studies: 502,
  // Mirrors science_corpus.json metadata; verify against /api/health vectorChunks after a corpus rebuild.
  chunks: 1264,
  joints: 8,
};
