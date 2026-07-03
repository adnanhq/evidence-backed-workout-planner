import type { EvidenceTier } from "@/types/protocol";

export interface TierMeta {
  label: string;
  short: string;
  rank: number; // 0 = strongest
  /** badge classes (bg + text + border) */
  badge: string;
  /** small dot color class */
  dot: string;
  definition: string;
}

/**
 * The evidence-tier hierarchy is the heart of the brand. Strong tiers get a
 * solid / tinted teal treatment; weak tiers fade to neutral grey so the eye
 * instantly reads study quality.
 */
export const EVIDENCE_TIERS: Record<EvidenceTier, TierMeta> = {
  meta_analysis: {
    label: "Meta-analysis",
    short: "Meta",
    rank: 0,
    badge: "bg-[#0f766e] text-white border-transparent",
    dot: "bg-[#0f766e]",
    definition:
      "Pools results across many studies — the strongest grade of evidence for a training effect.",
  },
  rct: {
    label: "RCT",
    short: "RCT",
    rank: 1,
    badge: "bg-[#cdeae5] text-[#0b5e57] border-[#86c8bd]",
    dot: "bg-[#0f766e]",
    definition:
      "Randomized controlled trial — participants randomly assigned, the gold standard single study.",
  },
  systematic_review: {
    label: "Systematic review",
    short: "Sys. review",
    rank: 2,
    badge: "bg-[#e3f2ef] text-[#0e6b63] border-[#a9d8d0]",
    dot: "bg-[#2f8f86]",
    definition:
      "A structured, comprehensive synthesis of the studies on a question.",
  },
  controlled_trial: {
    label: "Controlled trial",
    short: "Trial",
    rank: 3,
    badge: "bg-[#eef2f6] text-[#334155] border-[#d5d9e0]",
    dot: "bg-[#64748b]",
    definition: "A trial with a comparison group but without full randomization.",
  },
  observational: {
    label: "Observational",
    short: "Observational",
    rank: 4,
    badge: "bg-[#f2f4f7] text-[#5b6573] border-[#e2e6ec]",
    dot: "bg-[#94a3b8]",
    definition: "Measures outcomes without assigning the intervention.",
  },
  narrative_review: {
    label: "Narrative review",
    short: "Review",
    rank: 5,
    badge: "bg-[#f6f7f9] text-[#6b7280] border-[#e7e9ee]",
    dot: "bg-[#a8b0bd]",
    definition: "An expert overview of a topic, without a systematic method.",
  },
  other: {
    label: "Other evidence",
    short: "Other",
    rank: 6,
    badge: "bg-[#f6f7f9] text-[#8a94a3] border-[#eceef1]",
    dot: "bg-[#c2c8d2]",
    definition: "Supporting evidence that doesn't fit a higher tier.",
  },
};

export const TIER_ORDER: EvidenceTier[] = (
  Object.keys(EVIDENCE_TIERS) as EvidenceTier[]
).sort((a, b) => EVIDENCE_TIERS[a].rank - EVIDENCE_TIERS[b].rank);

export function tierMeta(tier: string | null | undefined): TierMeta {
  return EVIDENCE_TIERS[(tier as EvidenceTier) ?? "other"] ?? EVIDENCE_TIERS.other;
}

export function tierRank(tier: string | null | undefined): number {
  return tierMeta(tier).rank;
}

/** Strong = meta-analysis or RCT ("RCT-tier and above"). */
export function isStrongTier(tier: string | null | undefined): boolean {
  return tier === "meta_analysis" || tier === "rct";
}

export function pubmedUrl(pmid: string | null | undefined): string | null {
  if (!pmid) return null;
  return `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`;
}
