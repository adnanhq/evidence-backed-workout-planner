import type { GenerateResponse } from "@/types/protocol";
import { ENGINE_URL } from "./api";

const MEDIA = `${ENGINE_URL}/media/`;

/** Canned, realistic protocol for the landing-page live preview. */
export const DEMO_PROTOCOL: GenerateResponse = {
  request: {
    goal: "hypertrophy",
    muscles: ["chest", "biceps"],
    sessions: 2,
    sessionMinutes: 45,
    exercisesPerSession: null,
    equipment: ["dumbbell", "cable", "barbell"],
    experience: "intermediate",
    avoidJoints: [],
    notes: "",
    splitTemplate: "auto",
  },
  splitSummary: "Upper Body",
  splitTemplate: "auto",
  planner: "llm",
  plannerModel: null,
  usedFallback: false,
  exercisesPerSession: 3,
  warnings: [],
  sessions: [
    {
      sessionNumber: 1,
      splitLabel: "Upper Body — Chest Emphasis",
      focus: "Chest-led pressing with a biceps accessory",
      targetMuscles: ["chest", "biceps"],
      exercises: [
        {
          exerciseId: "0025",
          thumbnail: MEDIA + "images/0025-EIeI8Vf.jpg",
          name: "Barbell Bench Press",
          targetMuscle: "chest",
          targetLabel: "Chest",
          rankDisplay: "#1/168 · tied×25",
          selectionReason: "Top-ranked chest builder; 1 direct study match",
          lowerTrustEvidence: false,
          prescription: { sets: "3", reps: "8-10", rest: "120 sec", display: "3×8-10" },
          referencePmids: ["39593465"],
          referenceEvidence: [
            {
              pmid: "39593465",
              title:
                "Muscle hypertrophy response across four muscles involved in pressing after a resistance-training program.",
              year: 2024,
              tier: "rct",
              trustLabel: "standard",
              snippet:
                "Heavy compound pressing drove measurable hypertrophy across the pectoral and triceps regions.",
              url: "https://pubmed.ncbi.nlm.nih.gov/39593465/",
            },
          ],
        },
        {
          exerciseId: "0195",
          thumbnail: MEDIA + "images/0195-P2lNrGL.jpg",
          name: "Cable Preacher Curl",
          targetMuscle: "biceps",
          targetLabel: "Biceps",
          rankDisplay: "#4/151 · tied×27",
          selectionReason: "Directly targets the requested muscle; biceps rank #4/151",
          lowerTrustEvidence: false,
          prescription: { sets: "3", reps: "10-12", rest: "90 sec", display: "3×10-12" },
          referencePmids: ["40082069"],
          referenceEvidence: [
            {
              pmid: "40082069",
              title:
                "Shoulder-flexed vs. extended positions in elbow-flexion training: Preacher versus Bayesian cable curls.",
              year: 2025,
              tier: "rct",
              trustLabel: "standard",
              snippet:
                "The preacher variation outperformed the extended-shoulder position at several elbow-flexor sites.",
              url: "https://pubmed.ncbi.nlm.nih.gov/40082069/",
            },
          ],
        },
        {
          exerciseId: "0319",
          thumbnail: MEDIA + "images/0319-ESOd5Pl.jpg",
          name: "Dumbbell Incline Fly",
          targetMuscle: "chest",
          targetLabel: "Chest",
          rankDisplay: "#54/168 · tied×37",
          selectionReason: "Adds an upper-chest stretch emphasis",
          lowerTrustEvidence: true,
          prescription: { sets: "3", reps: "12-15", rest: "75 sec", display: "3×12-15" },
          referencePmids: [],
          referenceEvidence: [],
        },
      ],
    },
  ],
  evidenceAppendix: [
    {
      pmid: "40570881",
      title: "Does muscle length influence regional hypertrophy? A meta-analysis.",
      year: 2025,
      tier: "meta_analysis",
      trustLabel: "standard",
      snippet:
        "Training at longer muscle lengths can meaningfully improve regional hypertrophy outcomes.",
      url: "https://pubmed.ncbi.nlm.nih.gov/40570881/",
    },
    {
      pmid: "40082069",
      title:
        "Preacher versus Bayesian cable curls: shoulder position and regional elbow-flexor hypertrophy.",
      year: 2025,
      tier: "rct",
      trustLabel: "standard",
      snippet:
        "The preacher variation outperformed the extended-shoulder position at several elbow-flexor sites.",
      url: "https://pubmed.ncbi.nlm.nih.gov/40082069/",
    },
    {
      pmid: "39593465",
      title: "Muscle hypertrophy response across four muscles involved in pressing.",
      year: 2024,
      tier: "rct",
      trustLabel: "standard",
      snippet: "Heavy compound pressing drove measurable hypertrophy across pressing musculature.",
      url: "https://pubmed.ncbi.nlm.nih.gov/39593465/",
    },
  ],
  markdown: "",
};
