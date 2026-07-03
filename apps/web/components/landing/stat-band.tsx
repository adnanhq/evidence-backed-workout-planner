import { Reveal } from "@/components/layout/reveal";

const STATS = [
  { n: "1,324", l: "exercises analyzed" },
  { n: "502", l: "peer-reviewed studies" },
  { n: "RCT-tier", l: "evidence grading" },
  { n: "8", l: "joint-safety filters" },
];

export function StatBand() {
  return (
    <div className="border-y border-border bg-surface">
      <div className="mx-auto grid max-w-[var(--container-page)] grid-cols-2 divide-x divide-y divide-border px-0 sm:grid-cols-4 sm:divide-y-0">
        {STATS.map((s, i) => (
          <Reveal key={s.l} delay={i * 0.06} className="px-6 py-9 text-center">
            <div className="tnum font-mono text-3xl font-semibold text-ink sm:text-4xl">
              {s.n}
            </div>
            <div className="mt-1.5 text-[0.82rem] text-muted">{s.l}</div>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
