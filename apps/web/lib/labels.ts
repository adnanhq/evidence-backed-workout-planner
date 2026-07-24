import type { GenerateResponse } from "@/types/protocol";

export const MUSCLE_LABELS: Record<string, string> = {
  abs: "Abs",
  biceps: "Biceps",
  calves: "Calves",
  chest: "Chest",
  delts: "Shoulders",
  forearms: "Forearms",
  glutes: "Glutes",
  hamstrings: "Hamstrings",
  hip_abductors: "Hip Abductors",
  hip_adductors: "Hip Adductors",
  lats: "Lats",
  mid_back: "Mid Back",
  neck: "Neck",
  quads: "Quads",
  spinal_erectors: "Lower Back",
  traps: "Traps",
  triceps: "Triceps",
};

export const MUSCLE_REGIONS: { name: string; muscles: string[] }[] = [
  { name: "Push", muscles: ["chest", "delts", "triceps"] },
  { name: "Pull", muscles: ["lats", "mid_back", "traps", "biceps", "forearms"] },
  {
    name: "Legs",
    muscles: ["quads", "hamstrings", "glutes", "calves", "hip_abductors", "hip_adductors"],
  },
  { name: "Core & Other", muscles: ["abs", "spinal_erectors", "neck"] },
];

export const EQUIPMENT_LABELS: Record<string, string> = {
  barbell: "Barbell",
  bodyweight: "Bodyweight",
  cable: "Cable",
  dumbbell: "Dumbbell",
  ez_bar: "EZ Bar",
  foam_roller: "Foam Roller",
  kettlebell: "Kettlebell",
  machine: "Machine",
  medicine_ball: "Medicine Ball",
  other: "Other",
  resistance_band: "Resistance Band",
  stability_ball: "Stability Ball",
  smith_machine: "Smith Machine",
  leverage_machine: "Leverage Machine",
  sled_machine: "Sled Machine",
  weighted: "Weighted",
  assisted: "Assisted",
  rope: "Rope",
  cardio_machine: "Cardio Machine",
  unknown: "Unknown",
};

export const EQUIPMENT_PRESETS: Record<string, string[]> = {
  "Full gym": ["barbell", "cable", "dumbbell", "ez_bar", "machine", "leverage_machine", "smith_machine"],
  "Dumbbells only": ["dumbbell"],
  "Bodyweight only": ["bodyweight"],
  Home: ["dumbbell", "resistance_band", "bodyweight", "kettlebell"],
};

export const JOINT_LABELS: Record<string, string> = {
  neck: "Neck",
  shoulder: "Shoulder",
  elbow: "Elbow",
  wrist: "Wrist",
  spine: "Spine",
  hip: "Hip",
  knee: "Knee",
  ankle: "Ankle",
};

export const GOAL_LABELS: Record<string, string> = {
  hypertrophy: "Hypertrophy",
  strength: "Strength",
};

export const GOAL_BLURB: Record<string, string> = {
  hypertrophy: "Build muscle size — moderate reps, higher volume.",
  strength: "Build maximal force — heavier loads, lower reps.",
};

export const SPLIT_LABELS: Record<string, string> = {
  auto: "Auto",
  full_body: "Full Body",
  push_pull: "Push / Pull",
  push_pull_legs: "Push / Pull / Legs",
  upper_lower: "Upper / Lower",
};

export const SPLIT_BLURB: Record<string, string> = {
  auto: "We'll choose the best split for your muscles and schedule.",
  full_body: "Every session trains the whole body.",
  push_pull: "Alternate pushing and pulling days.",
  push_pull_legs: "Push, pull, and legs on separate days.",
  upper_lower: "Alternate upper-body and lower-body days.",
};

export const EXPERIENCE_LABELS: Record<string, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

export const EXPERIENCE_BLURB: Record<string, string> = {
  beginner: "New to lifting or returning after a long break.",
  intermediate: "Consistent training for 6+ months.",
  advanced: "Years of structured training.",
};

export function muscleLabel(m: string): string {
  return MUSCLE_LABELS[m] ?? titleCase(m);
}
export function equipmentLabel(e: string): string {
  return EQUIPMENT_LABELS[e] ?? titleCase(e);
}
export function jointLabel(j: string): string {
  return JOINT_LABELS[j] ?? titleCase(j);
}
export function splitLabel(s: string): string {
  return SPLIT_LABELS[s] ?? titleCase(s);
}

export function titleCase(s: string): string {
  return s
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Engine rank strings look like "#1/168 · tied×25". Pull out the rank and
 * pool size so the UI can phrase it in plain language; the tie-count suffix
 * is deliberately dropped from user-facing copy.
 */
export function parseRankDisplay(
  rankDisplay: string | null | undefined,
): { rank: number; total: number } | null {
  if (!rankDisplay) return null;
  const m = rankDisplay.match(/#(\d+)\s*\/\s*(\d+)/);
  if (!m) return null;
  return { rank: Number(m[1]), total: Number(m[2]) };
}

export function protocolRecapLine(data: GenerateResponse): string {
  const req = data.request;
  return [
    GOAL_LABELS[req.goal] ?? req.goal,
    `${req.sessions} ${req.sessions === 1 ? "session" : "sessions"}/week`,
    data.splitSummary ?? splitLabel(req.splitTemplate),
    req.equipment.length ? req.equipment.map(equipmentLabel).join(", ") : "any equipment",
  ]
    .filter(Boolean)
    .join("  ·  ");
}
