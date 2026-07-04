import { CountUp } from "./count-up";

const STATS = [
  { value: 1324, label: "exercises analyzed" },
  { value: 502, label: "peer-reviewed studies" },
  { value: 103, label: "PubMed queries" },
  { value: 147, label: "flagged for review" },
];

export function StatBand() {
  return (
    <div className="border-b border-border bg-surface">
      <div className="mx-auto grid max-w-[var(--container-page)] grid-cols-2 divide-x divide-y divide-border sm:grid-cols-4 sm:divide-y-0">
        {STATS.map((s) => (
          <div key={s.label} className="px-6 py-10 sm:px-8">
            <CountUp
              value={s.value}
              className="tnum block font-mono text-5xl font-semibold tracking-tight text-ink sm:text-6xl"
            />
            <div className="mt-3 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-subtle">
              {s.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
