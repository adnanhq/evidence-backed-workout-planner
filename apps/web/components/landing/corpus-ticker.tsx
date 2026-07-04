import Link from "next/link";
import { tierMeta } from "@/lib/evidence";
import { CORPUS_SAMPLE, type CorpusStudy } from "./corpus-sample";

function truncate(text: string, max = 72) {
  return text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text;
}

function TickerRow({ hidden }: { hidden?: boolean }) {
  return (
    <div
      aria-hidden={hidden || undefined}
      className="flex shrink-0 items-center gap-10 pr-10"
    >
      {CORPUS_SAMPLE.map((study: CorpusStudy) => (
        <span
          key={study.pmid}
          className="flex items-baseline gap-3 whitespace-nowrap font-mono text-[0.78rem]"
        >
          <span className="font-medium uppercase tracking-[0.08em] text-accent">
            {tierMeta(study.tier).short}
          </span>
          <span className="text-muted">{truncate(study.title)}</span>
          <span className="tnum text-subtle">
            PMID {study.pmid} · {study.year}
          </span>
        </span>
      ))}
    </div>
  );
}

/**
 * A slow marquee of real studies from the evidence corpus. Pure CSS animation
 * (`motion-safe:` keeps it static under reduced motion); the duplicate row is
 * aria-hidden and nothing inside the moving strip is focusable.
 */
export function CorpusTicker() {
  return (
    <section
      aria-label="A sample of the evidence corpus"
      className="border-y border-border bg-surface"
    >
      <div className="mask-fade-x overflow-hidden py-5">
        <div className="flex w-max motion-safe:animate-marquee hover:[animation-play-state:paused] lg:[animation-duration:90s]">
          <TickerRow />
          <TickerRow hidden />
        </div>
      </div>
      <div className="mx-auto flex w-full max-w-[var(--container-page)] items-baseline justify-between gap-4 border-t border-border px-5 py-3 sm:px-8">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-subtle">
          Sampled from a corpus of 502 graded studies
        </p>
        <Link
          href="/science#corpus"
          className="shrink-0 font-mono text-[0.72rem] text-muted underline-offset-4 hover:text-accent hover:underline"
        >
          Browse the methodology →
        </Link>
      </div>
    </section>
  );
}
