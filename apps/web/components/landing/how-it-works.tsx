import { CalendarCheck, Microscope, SlidersHorizontal } from "lucide-react";
import { Eyebrow, Section } from "@/components/layout/section";
import { Reveal } from "@/components/layout/reveal";

const STEPS = [
  {
    icon: SlidersHorizontal,
    n: "01",
    title: "Tell us your goal",
    body: "Choose your goal, target muscles, available equipment, and how many days a week you train.",
  },
  {
    icon: Microscope,
    n: "02",
    title: "We retrieve the science",
    body: "We filter 1,324 exercises to what actually fits you, then pull the matching peer-reviewed studies.",
  },
  {
    icon: CalendarCheck,
    n: "03",
    title: "Get a cited plan",
    body: "An AI planner lays out your week — every exercise ranked and linked to the evidence behind it.",
  },
];

export function HowItWorks() {
  return (
    <Section id="how" className="py-24 sm:py-28">
      <Reveal>
        <Eyebrow>How it works</Eyebrow>
        <h2 className="mt-3 max-w-2xl font-display text-3xl font-semibold leading-tight text-ink sm:text-[2.5rem]">
          From your goals to a cited plan — in three steps.
        </h2>
      </Reveal>

      <div className="mt-12 grid gap-5 md:grid-cols-3">
        {STEPS.map((step, i) => (
          <Reveal key={step.n} delay={i * 0.08}>
            <div className="h-full rounded-xl border border-border bg-surface p-6 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-border-strong hover:shadow-md">
              <div className="flex items-center justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-accent-subtle text-accent">
                  <step.icon className="h-5 w-5" />
                </div>
                <span className="tnum font-mono text-sm text-subtle">{step.n}</span>
              </div>
              <h3 className="mt-5 font-display text-xl font-medium text-ink">
                {step.title}
              </h3>
              <p className="mt-2 text-[0.92rem] leading-relaxed text-muted">
                {step.body}
              </p>
            </div>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}
