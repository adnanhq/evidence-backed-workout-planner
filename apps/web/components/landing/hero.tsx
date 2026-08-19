"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { buttonClasses } from "@/components/ui/button";
import { useHydrated } from "@/lib/use-hydrated";

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
    <section className="relative isolate -mt-16 overflow-hidden bg-surface">
      {/* Two whisper-quiet layers, nothing more: a hairline grid and one soft
          accent wash behind the headline. */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="bg-grid absolute inset-0 [mask-image:radial-gradient(60%_55%_at_50%_0%,black,transparent)]" />
        <div className="absolute inset-x-0 top-0 h-[34rem] bg-[radial-gradient(56%_56%_at_50%_-6%,rgba(15,118,110,0.075),transparent_72%)]" />
      </div>

      <div
        key={active ? "animated" : "static"}
        className="relative mx-auto w-full max-w-4xl px-5 pb-24 pt-32 text-center sm:px-8 sm:pb-28 sm:pt-40"
      >
        {/* Says what the product is before the headline is even read */}
        <motion.div {...rise(8, 0)}>
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-[0.66rem] font-semibold uppercase tracking-[0.1em] text-muted shadow-xs sm:px-3.5 sm:text-[0.72rem] sm:tracking-[0.14em]">
            <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-accent" />
            Evidence-based workout builder
          </span>
        </motion.div>

        <motion.h1
          {...rise(16, 0.06)}
          className="mx-auto mt-8 max-w-[32ch] text-balance font-display text-[clamp(2.15rem,4.4vw,3.6rem)] font-semibold leading-[1.06] tracking-[-0.03em] text-ink"
        >
          {/* Keeping the compound whole stops narrow screens from breaking it
              into "peer-" / "reviewed". */}
          Your workout plan, built from{" "}
          <span className="whitespace-nowrap">peer-reviewed</span> research.
        </motion.h1>

        <motion.p
          {...rise(16, 0.12)}
          className="mx-auto mt-6 max-w-[56ch] text-pretty text-[1.0625rem] leading-relaxed text-muted sm:text-lg"
        >
          Tell Axiom your goal, your equipment and the days you can train. It
          ranks 1,324 exercises against 502 peer-reviewed studies and lays out
          your training week — with a link to the paper behind every set.
        </motion.p>

        <motion.div
          {...rise(16, 0.18)}
          className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4"
        >
          <Link
            href="/build"
            className={buttonClasses("primary", "lg", "w-full sm:w-auto")}
          >
            Build your plan <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/#sample"
            className={buttonClasses("outline", "lg", "w-full sm:w-auto")}
          >
            See a sample plan
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
