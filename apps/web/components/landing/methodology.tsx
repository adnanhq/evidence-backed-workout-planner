import { BarChart3, CalendarRange, Database, Search } from "lucide-react";
import { Eyebrow, Section } from "@/components/layout/section";
import { Reveal } from "@/components/layout/reveal";
import { TierLegend } from "@/components/evidence/tier-legend";

const PIPELINE = [
  {
    icon: Database,
    title: "Evidence corpus",
    body: "502 PubMed studies, each graded by type — from meta-analyses down to observational reports.",
  },
  {
    icon: Search,
    title: "Semantic retrieval",
    body: "We match studies to your exact muscles and movements, not just keywords.",
  },
  {
    icon: BarChart3,
    title: "Evidence ranking",
    body: "Every exercise is scored on study quality, goal fit, and joint stress.",
  },
  {
    icon: CalendarRange,
    title: "Weekly plan",
    body: "An AI planner places the top-ranked picks across your training week.",
  },
];

export function Methodology() {
  return (
    <Section id="science" className="py-24 sm:py-28">
      <div className="grid gap-14 lg:grid-cols-2 lg:gap-20">
        <Reveal>
          <Eyebrow>Methodology</Eyebrow>
          <h2 className="mt-3 font-display text-3xl font-semibold leading-tight text-ink sm:text-[2.5rem]">
            Why you can trust these recommendations
          </h2>
          <p className="mt-5 text-[0.98rem] leading-relaxed text-muted">
            Most training advice is opinion dressed as fact. Protocol starts from the
            literature instead: a curated corpus of peer-reviewed studies, each graded
            by the strength of its evidence.
          </p>
          <p className="mt-3 text-[0.98rem] leading-relaxed text-muted">
            When you build a plan, we retrieve the studies that match your muscles and
            movements, rank exercises by evidence quality and fit, and surface every
            citation so you can verify it yourself.
          </p>

          <div id="tiers" className="mt-8 rounded-xl border border-border bg-surface p-5 shadow-card">
            <p className="text-[0.76rem] font-semibold uppercase tracking-[0.1em] text-subtle">
              Evidence tiers — strongest first
            </p>
            <TierLegend className="mt-4" />
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="space-y-3">
            {PIPELINE.map((p, i) => (
              <div
                key={p.title}
                className="relative flex gap-4 rounded-xl border border-border bg-surface p-5 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-border-strong hover:shadow-md"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-subtle text-accent">
                  <p.icon className="h-5 w-5" />
                </div>
                <div className="pr-8">
                  <h3 className="font-medium text-ink">{p.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{p.body}</p>
                </div>
                <span className="tnum absolute right-4 top-4 font-mono text-xs text-subtle">
                  0{i + 1}
                </span>
              </div>
            ))}
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
