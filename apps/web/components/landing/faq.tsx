import { ChevronDown } from "lucide-react";
import { Eyebrow, Section } from "@/components/layout/section";
import { Reveal } from "@/components/layout/reveal";

const FAQS = [
  {
    q: "Where does the evidence come from?",
    a: "A curated corpus of 502 peer-reviewed studies from PubMed/NCBI, each graded by evidence type. Every recommendation links to the source so you can read it yourself.",
  },
  {
    q: "What do the evidence tiers mean?",
    a: "They rank how reliable a study is. Meta-analyses and randomized controlled trials (RCTs) are the strongest; narrative reviews and observational studies are weaker. We always show the tier.",
  },
  {
    q: "What if there isn't strong evidence for an exercise?",
    a: "We tell you. Exercises chosen on biomechanical reasoning rather than a direct study are labeled, and weaker citations are flagged 'lower-trust' — we never hide it.",
  },
  {
    q: "Can I pick my equipment and protect certain joints?",
    a: "Yes. Tell us what equipment you have and which joints to ease load on, and we only suggest exercises that fit — down-ranking ones that stress the joints you flag.",
  },
  {
    q: "Is this medical advice?",
    a: "No. Protocol is an educational tool that surfaces published research. It is not a substitute for professional medical or coaching advice.",
  },
];

export function Faq() {
  return (
    <Section className="py-24 sm:py-28">
      <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr]">
        <Reveal>
          <Eyebrow>FAQ</Eyebrow>
          <h2 className="mt-3 font-display text-3xl font-semibold leading-tight text-ink sm:text-[2.5rem]">
            Questions, answered honestly.
          </h2>
          <p className="mt-3 text-[0.98rem] leading-relaxed text-muted">
            How the evidence works — and where its limits are.
          </p>
        </Reveal>

        <Reveal delay={0.06}>
          <div className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-surface shadow-card">
            {FAQS.map((f) => (
              <details key={f.q} className="group px-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 text-[0.98rem] font-medium text-ink [&::-webkit-details-marker]:hidden">
                  {f.q}
                  <ChevronDown className="h-4 w-4 shrink-0 text-subtle transition-transform group-open:rotate-180" />
                </summary>
                <p className="pb-4 text-[0.9rem] leading-relaxed text-muted">{f.a}</p>
              </details>
            ))}
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
