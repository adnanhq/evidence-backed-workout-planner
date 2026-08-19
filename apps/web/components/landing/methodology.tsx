import { Section } from "@/components/layout/section";
import { Reveal } from "@/components/layout/reveal";
import { TierLegend } from "@/components/evidence/tier-legend";
import { LedgerHeading } from "./ledger";

const STAGES = [
  {
    n: "02.1",
    title: "Corpus",
    body: "502 PubMed studies, each graded by evidence tier — from meta-analyses down to observational reports.",
  },
  {
    n: "02.2",
    title: "Retrieval",
    body: "Semantic search matches studies to your exact muscles and movements, not just keywords.",
  },
  {
    n: "02.3",
    title: "Ranking",
    body: "Every exercise is scored on study quality, goal fit, and joint stress.",
  },
  {
    n: "02.4",
    title: "Plan",
    body: "A planner places the top-ranked picks across your training week — citations attached.",
  },
];

export function Methodology() {
  return (
    <Section id="science" className="py-24 sm:py-32">
      <Reveal>
        <LedgerHeading
          index="02"
          label="Methodology"
          title="Why you can trust these recommendations."
        />
      </Reveal>

      <div className="mt-12 grid gap-14 lg:grid-cols-2 lg:gap-20">
        <Reveal>
          <p className="text-[0.98rem] leading-relaxed text-muted">
            Most training advice is opinion dressed as fact. Axiom starts
            from the literature instead: a curated corpus of peer-reviewed
            studies, each graded by the strength of its evidence.
          </p>
          <p className="mt-3 text-[0.98rem] leading-relaxed text-muted">
            When you build a plan, the studies that match your muscles and
            movements are retrieved, exercises are ranked by evidence quality
            and fit, and every citation is surfaced so you can verify it
            yourself.
          </p>

          <div id="tiers" className="mt-10 scroll-mt-24 border-t border-border pt-6">
            <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-subtle">
              Evidence tiers — strongest first
            </p>
            <TierLegend className="mt-5" />
          </div>
        </Reveal>

        {/* Pipeline as a vertical trace — echoes the hero's evidence trace */}
        <Reveal delay={0.1}>
          <div className="border-l border-border">
            {STAGES.map((stage) => (
              <div key={stage.n} className="relative pb-10 pl-8 last:pb-0">
                <span
                  aria-hidden
                  className="absolute -left-px top-1.5 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-accent ring-4 ring-bg"
                />
                <div className="flex items-baseline gap-3">
                  <span className="tnum font-mono text-sm text-subtle">
                    {stage.n}
                  </span>
                  <h3 className="font-display text-lg font-medium text-ink">
                    {stage.title}
                  </h3>
                </div>
                <p className="mt-2 max-w-md text-sm leading-relaxed text-muted">
                  {stage.body}
                </p>
              </div>
            ))}
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
