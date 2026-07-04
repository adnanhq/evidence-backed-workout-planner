import { Section } from "@/components/layout/section";
import { Reveal } from "@/components/layout/reveal";
import { LedgerHeading } from "./ledger";

const STEPS = [
  {
    n: "01.1",
    title: "State your constraints",
    body: "Your goal, target muscles, available equipment, training days — and any joints you need to protect.",
  },
  {
    n: "01.2",
    title: "The corpus is filtered",
    body: "1,324 exercises are narrowed to the ones that fit you, and the matching peer-reviewed studies are retrieved.",
  },
  {
    n: "01.3",
    title: "You get a cited plan",
    body: "A planner lays out your week — every exercise ranked, every prescription linked to the evidence behind it.",
  },
];

export function HowItWorks() {
  return (
    <Section id="how" className="py-24 sm:py-32">
      <div className="grid gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:gap-20">
        <div className="lg:sticky lg:top-24 lg:self-start">
          <Reveal>
            <LedgerHeading
              index="01"
              label="How it works"
              title="From your constraints to a cited plan."
            >
              <p>
                Tell Protocol what you have and what you&apos;re training for.
                It does the reading.
              </p>
            </LedgerHeading>
          </Reveal>
        </div>

        <div>
          {STEPS.map((step, i) => (
            <Reveal key={step.n} delay={i * 0.06}>
              <div className="grid grid-cols-[3.5rem_1fr] border-t border-border py-8 last:border-b sm:py-9">
                <span className="tnum pt-1 font-mono text-sm text-subtle">
                  {step.n}
                </span>
                <div>
                  <h3 className="font-display text-xl font-medium text-ink sm:text-2xl">
                    {step.title}
                  </h3>
                  <p className="mt-2.5 max-w-lg text-[0.95rem] leading-relaxed text-muted">
                    {step.body}
                  </p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </Section>
  );
}
