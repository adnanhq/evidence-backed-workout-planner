"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { buttonClasses } from "@/components/ui/button";
import { useHydrated } from "@/lib/use-hydrated";
import { EvidenceTrace } from "./evidence-trace";
import { FootnoteBand, Sup } from "./footnote";
import { HERO_CITATION } from "./corpus-sample";

const ease = [0.22, 1, 0.36, 1] as const;

export function Hero() {
  const hydrated = useHydrated();
  const reduced = useReducedMotion();

  // Server HTML ships fully visible (no-JS visitors and LCP both need the
  // headline painted); after hydration a keyed remount replays the entrance.
  // Reduced-motion clients keep the static tree.
  const active = hydrated && !reduced;
  const rise = (y: number, delay: number) =>
    active
      ? {
          initial: { opacity: 0, y },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.6, delay, ease },
        }
      : {};

  return (
    <section className="relative isolate -mt-16 overflow-hidden bg-ink-surface text-on-dark">
      {/* Decorative layers */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="aurora absolute inset-0" />
        <div className="bg-grid-dark absolute inset-0 opacity-60 [mask-image:radial-gradient(80%_60%_at_50%_0%,black,transparent)]" />
        <div className="absolute left-1/2 top-[-12rem] h-[26rem] w-[42rem] -translate-x-1/2 rounded-full bg-glow-teal/20 blur-3xl" />
      </div>

      <div
        key={active ? "animated" : "static"}
        className="relative mx-auto w-full max-w-[var(--container-page)] px-5 pt-28 sm:px-8 sm:pt-36"
      >
        {/* Ledger line */}
        <motion.div {...rise(10, 0)} className="flex items-center gap-4">
          <span className="font-mono text-[0.7rem] uppercase tracking-[0.2em] text-on-dark-subtle">
            Protocol / Evidence-based training
          </span>
          <span aria-hidden className="hidden flex-1 border-t border-on-dark-border sm:block" />
        </motion.div>

        <div className="mt-10 grid items-start gap-14 lg:grid-cols-[1.05fr_0.95fr] lg:gap-20">
          {/* Headline + lede + CTAs */}
          <div>
            <motion.h1
              {...rise(16, 0.05)}
              className="font-display text-[clamp(3.25rem,5.2vw,5.25rem)] font-semibold leading-[0.98] tracking-[-0.03em] text-on-dark"
            >
              Every set in your program, cited.
              <Sup n={1} targetId="fn-1" />
            </motion.h1>

            <motion.p
              {...rise(16, 0.12)}
              className="mt-8 max-w-xl text-lg leading-relaxed text-on-dark-muted"
            >
              Protocol ranks 1,324 exercises against 502 graded studies and
              shows you the paper behind every prescription.
            </motion.p>

            <motion.div
              {...rise(16, 0.18)}
              className="mt-10 flex flex-wrap items-center gap-x-8 gap-y-4"
            >
              <Link
                href="/build"
                className={buttonClasses("primary", "lg", "shadow-glow-teal")}
              >
                Build your protocol <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/science"
                className="font-mono text-[0.82rem] font-medium text-on-dark-muted underline decoration-on-dark-border-strong underline-offset-8 transition-colors hover:text-on-dark hover:decoration-accent-on-dark"
              >
                Read the methodology →
              </Link>
            </motion.div>
          </div>

          {/* Evidence trace */}
          <div className="relative mx-auto w-full max-w-md lg:max-w-none">
            <div
              aria-hidden
              className="pointer-events-none absolute -inset-6 rounded-[2rem] bg-glow-teal/15 blur-3xl"
            />
            <EvidenceTrace className="relative" />
          </div>
        </div>

        {/* Citation register — the hero's footnote resolves here */}
        <motion.div {...rise(12, 0.3)}>
          <FootnoteBand
            tone="dark"
            className="mt-16 pb-10 sm:mt-20 sm:pb-12"
            items={[
              {
                n: 1,
                id: "fn-1",
                label: `${HERO_CITATION.title} ${HERO_CITATION.source}`,
                pmid: HERO_CITATION.pmid,
              },
            ]}
            aside="1,324 exercises · 502 studies · every set cited"
          />
        </motion.div>
      </div>

      {/* Hairline transition to the light band below */}
      <div aria-hidden className="absolute inset-x-0 bottom-0 h-px bg-on-dark-border" />
    </section>
  );
}
