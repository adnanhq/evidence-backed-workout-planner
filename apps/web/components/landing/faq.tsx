import { Section } from "@/components/layout/section";
import { Reveal } from "@/components/layout/reveal";
import { LedgerHeading } from "./ledger";

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
    q: "What if the evidence is weak?",
    a: "We tell you. Exercises chosen on biomechanical reasoning rather than a direct study are labeled, and weaker citations are flagged 'lower-trust' — we never hide it.",
  },
  {
    q: "Can I protect specific joints?",
    a: "Yes. Tell us what equipment you have and which joints to ease load on, and we only suggest exercises that fit — down-ranking ones that stress the joints you flag.",
  },
  {
    q: "Is this medical advice?",
    a: "No. Protocol is an educational tool that surfaces published research. It is not a substitute for professional medical or coaching advice.",
  },
];

export function Faq() {
  return (
    <Section className="py-24 sm:py-32">
      <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
        <Reveal>
          <LedgerHeading index="04" label="FAQ" title="Questions, answered honestly.">
            <p>How the evidence works — and where its limits are.</p>
          </LedgerHeading>
        </Reveal>

        <Reveal delay={0.06}>
          <div>
            {FAQS.map((f, i) => (
              <details key={f.q} className="group border-t border-border last:border-b">
                <summary className="grid cursor-pointer list-none grid-cols-[3.5rem_1fr_auto] items-baseline gap-3 py-5 [&::-webkit-details-marker]:hidden">
                  <span className="tnum font-mono text-sm text-subtle">
                    04.{i + 1}
                  </span>
                  <span className="text-[0.98rem] font-medium text-ink">
                    {f.q}
                  </span>
                  <span
                    aria-hidden
                    className="font-mono text-lg leading-none text-subtle transition-transform duration-200 ease-soft group-open:rotate-45"
                  >
                    +
                  </span>
                </summary>
                <p className="pb-6 pl-[3.75rem] pr-8 text-[0.9rem] leading-relaxed text-muted">
                  {f.a}
                </p>
              </details>
            ))}
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
