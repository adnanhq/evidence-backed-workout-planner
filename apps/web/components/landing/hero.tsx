"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, ArrowUpRight, TrendingUp } from "lucide-react";
import { buttonClasses } from "@/components/ui/button";
import { EvidenceBadge } from "@/components/evidence/evidence-badge";

const ease = [0.22, 1, 0.36, 1] as const;

export function Hero() {
  const reduced = useReducedMotion();

  // With reduced motion, render in the final position with no transform/fade.
  const rise = (y: number, delay: number) =>
    reduced
      ? { initial: false as const }
      : {
          initial: { opacity: 0, y },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.6, delay, ease },
        };

  return (
    <section className="relative isolate -mt-16 overflow-hidden bg-ink-surface text-on-dark">
      {/* Decorative layers */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="aurora absolute inset-0" />
        <div className="bg-grid-dark absolute inset-0 opacity-60 [mask-image:radial-gradient(80%_60%_at_50%_0%,black,transparent)]" />
        <div className="absolute left-1/2 top-[-12rem] h-[26rem] w-[42rem] -translate-x-1/2 rounded-full bg-glow-teal/20 blur-3xl" />
      </div>

      <div className="relative mx-auto grid max-w-[var(--container-page)] items-center gap-12 px-5 pb-24 pt-28 sm:px-8 sm:pt-36 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:pb-32">
        {/* Copy column */}
        <div className="text-center lg:text-left">
          <motion.span
            {...rise(10, 0)}
            className="glass-dark inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-[0.74rem] font-medium text-on-dark-muted"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-accent-on-dark" />
            Evidence-based resistance training
          </motion.span>

          <motion.h1
            {...rise(16, 0.05)}
            className="mx-auto mt-6 max-w-2xl font-display text-[2.7rem] font-semibold leading-[1.04] tracking-tight text-on-dark sm:text-[4rem] lg:mx-0 lg:text-[4.25rem]"
          >
            Training built on <span className="text-accent-on-dark">evidence</span>,
            not opinion.
          </motion.h1>

          <motion.p
            {...rise(16, 0.12)}
            className="mx-auto mt-6 max-w-xl text-lg leading-relaxed text-on-dark-muted lg:mx-0"
          >
            Generate a peer-reviewed weekly protocol in seconds — every exercise
            ranked, and every suggestion linked to the study behind it.
          </motion.p>

          <motion.div
            {...rise(16, 0.18)}
            className="mt-9 flex flex-wrap items-center justify-center gap-3 lg:justify-start"
          >
            <Link
              href="/build"
              className={buttonClasses("primary", "lg", "shadow-glow-teal")}
            >
              Build your protocol <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/science"
              className={buttonClasses(
                "outline",
                "lg",
                "border-on-dark-border-strong bg-white/5 text-on-dark backdrop-blur hover:border-accent-on-dark hover:text-accent-on-dark",
              )}
            >
              See the science
            </Link>
          </motion.div>

          <motion.p
            {...rise(16, 0.24)}
            className="tnum mt-8 text-[0.72rem] font-medium uppercase tracking-[0.14em] text-on-dark-subtle"
          >
            1,324 exercises · 502 PubMed studies · every set cited
          </motion.p>
        </div>

        {/* Glassy product preview */}
        <motion.div
          {...(reduced
            ? { initial: false as const }
            : {
                initial: { opacity: 0, y: 24 },
                animate: { opacity: 1, y: 0 },
                transition: { duration: 0.7, delay: 0.3, ease },
              })}
          className="relative mx-auto w-full max-w-md lg:max-w-none"
        >
          <div
            aria-hidden
            className="pointer-events-none absolute -inset-6 rounded-[2rem] bg-glow-teal/15 blur-3xl"
          />
          <div className="glass-dark relative rounded-2xl p-5 shadow-on-dark">
            <p className="mb-3 text-[0.7rem] font-medium uppercase tracking-[0.14em] text-on-dark-subtle">
              Every suggestion is traceable
            </p>

            {/* Ranked exercise line — reads as the product */}
            <div className="flex items-center justify-between gap-3 rounded-xl border border-on-dark-border bg-ink-surface-2/60 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-on-dark">
                  Barbell Bench Press
                </p>
                <p className="mt-0.5 text-[0.78rem] text-on-dark-muted">
                  Chest · 3 × 8–10
                </p>
              </div>
              <span className="tnum inline-flex shrink-0 items-center gap-1 rounded-full bg-white/5 px-2 py-0.5 text-[0.7rem] font-medium text-accent-on-dark">
                <TrendingUp className="h-3 w-3" /> #1 / 168
              </span>
            </div>

            {/* Evidence citation */}
            <div className="mt-3 rounded-xl border border-on-dark-border bg-ink-surface-2/60 p-3.5">
              <div className="flex items-center gap-2">
                <EvidenceBadge tier="rct" size="sm" />
                <span className="tnum text-xs text-on-dark-subtle">2023</span>
              </div>
              <p className="mt-2 text-sm font-medium leading-snug text-on-dark">
                Effects of 12 weeks of resistance training on regional muscle
                hypertrophy.
              </p>
              <a
                href="https://pubmed.ncbi.nlm.nih.gov/39077025/"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-[0.8rem] font-medium text-accent-on-dark hover:underline"
              >
                View on PubMed <ArrowUpRight className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Hairline transition to the light StatBand below */}
      <div aria-hidden className="absolute inset-x-0 bottom-0 h-px bg-on-dark-border" />
    </section>
  );
}
