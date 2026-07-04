"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { useHydrated } from "@/lib/use-hydrated";
import { ArrowUpRight, TrendingUp } from "lucide-react";
import { EvidenceBadge } from "@/components/evidence/evidence-badge";
import { pubmedUrl } from "@/lib/evidence";
import { cn } from "@/lib/utils";
import { HERO_CITATION } from "./corpus-sample";

const EASE = [0.22, 1, 0.36, 1] as const;

/** One timeline for the whole choreography (seconds). */
const T = {
  scan: 0.25,
  select: 0.75,
  study: 1.0,
  line1: 1.6,
  exercise: 1.95,
  line2: 2.5,
  place: 2.7,
  ambient: 4.5,
};

const EXERCISE = { name: "Barbell Bench Press", detail: "Chest · 3 × 8–10", rank: "#1 / 168" };
const PLACEMENT = "Tuesday · Upper Body";

const TICK_COUNT = 56;
const SELECTED_TICK = 34;
const FLICKER_TICKS = [12, 45];
// Deterministic heights — SSR markup must match the client exactly.
const tickHeight = (i: number) => 8 + ((i * 37) % 11);

const ARIA_LABEL =
  `Evidence pipeline: from 502 PubMed studies, a ${HERO_CITATION.year} randomized controlled trial ` +
  `(PMID ${HERO_CITATION.pmid}) on regional muscle hypertrophy ranks ${EXERCISE.name} first of 168 ` +
  `chest exercises, programmed for 3 sets of 8 to 10 reps in Tuesday's upper-body session.`;

const rise = (delay: number, y = 10): Variants => ({
  hidden: { opacity: 0, y },
  show: { opacity: 1, y: 0, transition: { delay, duration: 0.5, ease: EASE } },
});

/**
 * The hero centerpiece: an animated trace of the product's pipeline —
 * corpus → study → ranked exercise → placement in the week. Plays once on
 * mount; SSR, no-JS, and reduced-motion all render the finished frame.
 */
export function EvidenceTrace({ className }: { className?: string }) {
  const reduced = useReducedMotion();
  const mounted = useHydrated();
  const animated = mounted && !reduced;

  // Keyed remount: motion components read `initial` only at mount, so the
  // static poster frame (server HTML) swaps to the playing tree after hydration.
  return (
    <TraceInner
      key={animated ? "play" : "static"}
      animated={animated}
      className={className}
    />
  );
}

function TraceInner({
  animated,
  className,
}: {
  animated: boolean;
  className?: string;
}) {
  // Spread variants only when animating; the static tree carries no motion props.
  const av = (variants: Variants) => (animated ? { variants } : {});

  return (
    <div className={cn("relative w-full", className)}>
      <motion.div
        role="img"
        aria-label={ARIA_LABEL}
        {...(animated ? { initial: "hidden", animate: "show" } : {})}
        {...av({
          hidden: { opacity: 0, y: 24 },
          show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
        })}
      >
        <div
          aria-hidden
          className="glass-dark relative rounded-2xl p-4 shadow-on-dark sm:p-5"
        >
          {/* Kicker */}
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-[0.7rem] font-medium uppercase tracking-[0.14em] text-on-dark-subtle">
              Every suggestion is traceable
            </p>
            <p className="tnum shrink-0 font-mono text-[0.7rem] text-on-dark-subtle">
              502 studies
            </p>
          </div>

          {/* Corpus row */}
          <motion.div
            className="mt-4 flex h-6 items-center justify-between"
            {...av({
              hidden: {},
              show: {
                transition: { delayChildren: T.scan, staggerChildren: 0.006 },
              },
            })}
          >
            {Array.from({ length: TICK_COUNT }, (_, i) => (
              <motion.span
                key={i}
                className="relative w-0.5 rounded-full bg-white/20"
                style={{ height: tickHeight(i) }}
                {...av({
                  hidden: { opacity: 0 },
                  show: { opacity: 1, transition: { duration: 0.25 } },
                })}
              >
                {i === SELECTED_TICK && (
                  <>
                    {/* Steady selection highlight (static glow, animated opacity) */}
                    <motion.span
                      className={cn(
                        "absolute -inset-x-px -inset-y-1 rounded-full bg-accent-on-dark",
                        !animated && "opacity-90",
                      )}
                      style={{ boxShadow: "0 0 12px rgba(94, 234, 212, 0.7)" }}
                      {...av({
                        hidden: { opacity: 0 },
                        show: {
                          opacity: 0.9,
                          transition: { delay: T.select, duration: 0.35, ease: EASE },
                        },
                      })}
                    />
                    {/* Ambient shimmer on top of the steady highlight */}
                    {animated && (
                      <motion.span
                        className="absolute -inset-x-px -inset-y-1 rounded-full bg-accent-on-dark"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: [0, 0.5, 0] }}
                        transition={{
                          delay: T.ambient,
                          duration: 4,
                          repeat: Infinity,
                          repeatDelay: 2,
                          ease: "easeInOut",
                        }}
                      />
                    )}
                  </>
                )}
                {animated && FLICKER_TICKS.includes(i) && (
                  <motion.span
                    className="absolute inset-0 rounded-full bg-accent-on-dark"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: [0, 0.45, 0] }}
                    transition={{
                      delay: T.ambient + (i === FLICKER_TICKS[0] ? 0 : 3.5),
                      duration: 1.4,
                      times: [0, 0.4, 1],
                      repeat: Infinity,
                      repeatDelay: 7,
                      ease: "easeInOut",
                    }}
                  />
                )}
              </motion.span>
            ))}
          </motion.div>

          {/* Study card */}
          <motion.div
            {...av(rise(T.study))}
            className="mt-4 rounded-xl border border-on-dark-border bg-ink-surface-2/70 p-3.5"
          >
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <EvidenceBadge tier={HERO_CITATION.tier} size="sm" />
              <span className="tnum font-mono text-[0.68rem] text-on-dark-subtle">
                PMID {HERO_CITATION.pmid}
              </span>
              <span className="tnum text-xs text-on-dark-subtle">
                {HERO_CITATION.year}
              </span>
            </div>
            <p className="mt-2 line-clamp-2 text-sm font-medium leading-snug text-on-dark">
              {HERO_CITATION.title}
            </p>
          </motion.div>

          <Connector h={28} delay={T.line1} id="et-g1" animated={animated} />

          {/* Ranked exercise */}
          <motion.div
            {...av({
              hidden: { opacity: 0, y: 8, scale: 0.98 },
              show: {
                opacity: 1,
                y: 0,
                scale: 1,
                transition: { delay: T.exercise, duration: 0.45, ease: EASE },
              },
            })}
            className="flex items-center justify-between gap-3 rounded-xl border border-on-dark-border bg-ink-surface-2/70 px-4 py-3"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-on-dark">
                {EXERCISE.name}
              </p>
              <p className="mt-0.5 text-[0.78rem] text-on-dark-muted">
                {EXERCISE.detail}
              </p>
            </div>
            <span className="tnum inline-flex shrink-0 items-center gap-1 rounded-full bg-white/5 px-2 py-0.5 font-mono text-[0.7rem] font-medium text-accent-on-dark">
              <TrendingUp className="h-3 w-3" /> {EXERCISE.rank}
            </span>
          </motion.div>

          <Connector h={20} delay={T.line2} id="et-g2" animated={animated} />

          {/* Placement in the week */}
          <motion.span
            {...av({
              hidden: { opacity: 0, scale: 0.92 },
              show: {
                opacity: 1,
                scale: 1,
                transition: { delay: T.place, duration: 0.45, ease: EASE },
              },
            })}
            className="inline-flex items-center gap-1.5 rounded-full border border-accent-on-dark/30 bg-accent-on-dark/10 px-3 py-1 text-xs font-medium text-accent-on-dark"
          >
            → {PLACEMENT}
          </motion.span>
        </div>
      </motion.div>

      {/* Real link, outside the role="img" region so it stays focusable */}
      <a
        href={pubmedUrl(HERO_CITATION.pmid)!}
        target="_blank"
        rel="noopener noreferrer"
        className="tnum mt-3 inline-flex items-center gap-1 font-mono text-[0.72rem] text-on-dark-subtle transition-colors hover:text-accent-on-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-on-dark"
      >
        Source: PMID {HERO_CITATION.pmid} · PubMed
        <ArrowUpRight className="h-3 w-3" aria-hidden />
      </a>
    </div>
  );
}

function Connector({
  h,
  delay,
  id,
  animated,
}: {
  h: number;
  delay: number;
  id: string;
  animated: boolean;
}) {
  return (
    <div className="relative" style={{ height: h }} aria-hidden>
      <svg
        className="absolute left-6 top-0"
        width="2"
        height={h}
        viewBox={`0 0 2 ${h}`}
        fill="none"
      >
        <defs>
          <linearGradient
            id={id}
            x1="0"
            y1="0"
            x2="0"
            y2={h}
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0" stopColor="#5eead4" stopOpacity="0.9" />
            <stop offset="1" stopColor="#5eead4" stopOpacity="0" />
          </linearGradient>
        </defs>
        {animated ? (
          <motion.path
            d={`M1 0 V ${h}`}
            stroke={`url(#${id})`}
            strokeWidth="2"
            strokeLinecap="round"
            variants={{
              hidden: { pathLength: 0, opacity: 0 },
              show: {
                pathLength: 1,
                opacity: 1,
                transition: { delay, duration: 0.4, ease: "easeInOut" },
              },
            }}
          />
        ) : (
          <path
            d={`M1 0 V ${h}`}
            stroke={`url(#${id})`}
            strokeWidth="2"
            strokeLinecap="round"
          />
        )}
      </svg>
    </div>
  );
}
