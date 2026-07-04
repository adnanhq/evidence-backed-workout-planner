import type { EvidenceTier } from "@/types/protocol";

export interface CorpusStudy {
  pmid: string;
  title: string;
  year: number;
  tier: EvidenceTier;
}

/**
 * Hand-curated sample of the 502-study corpus for the landing-page ticker.
 * Every PMID is real and present in the engine's evidence corpus.
 */
export const CORPUS_SAMPLE: CorpusStudy[] = [
  {
    pmid: "40570881",
    title:
      "Does muscle length influence regional hypertrophy? A systematic review and meta-analysis",
    year: 2025,
    tier: "meta_analysis",
  },
  {
    pmid: "39794667",
    title:
      "Muscle growth and dynamic strength adaptations from unilateral vs. bilateral resistance training",
    year: 2025,
    tier: "meta_analysis",
  },
  {
    pmid: "35819335",
    title:
      "Triceps hypertrophy is substantially greater after overhead vs. neutral-position elbow extension",
    year: 2023,
    tier: "rct",
  },
  {
    pmid: "40082069",
    title:
      "Shoulder-flexed vs. extended positions in elbow-flexion training: preacher vs. Bayesian cable curls",
    year: 2025,
    tier: "rct",
  },
  {
    pmid: "39593465",
    title:
      "Muscle hypertrophy response across four muscles involved in the bench press",
    year: 2024,
    tier: "rct",
  },
  {
    pmid: "40644669",
    title:
      "Minimal role of hamstring hypertrophy in strength transfer between Nordic curl and stiff-leg deadlift",
    year: 2025,
    tier: "rct",
  },
  {
    pmid: "40586278",
    title:
      "Hamstring activation strategies after selective hypertrophy from Nordic curl and stiff-leg deadlift",
    year: 2025,
    tier: "controlled_trial",
  },
  {
    pmid: "39995432",
    title:
      "Resistance training beyond momentary failure: past-failure partials and gastrocnemius hypertrophy",
    year: 2025,
    tier: "rct",
  },
  {
    pmid: "39077025",
    title:
      "Effects of 12 weeks of resistance training on body composition, muscle hypertrophy and function",
    year: 2023,
    tier: "rct",
  },
];

/** The study cited by the hero headline's footnote and the evidence trace. */
export const HERO_CITATION = {
  pmid: "39077025",
  year: 2023,
  tier: "rct" as EvidenceTier,
  title:
    "Effects of 12 weeks of resistance training on regional muscle hypertrophy.",
  source: "Rev Cardiovasc Med (2023)",
};
