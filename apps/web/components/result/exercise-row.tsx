"use client";

import { useId, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { parseRankDisplay } from "@/lib/labels";
import { useExerciseThumbnail } from "@/lib/queries";
import type { ProtocolExercise } from "@/types/protocol";
import { EvidenceCard } from "@/components/evidence/evidence-card";
import { LowerTrustPill } from "@/components/evidence/lower-trust-pill";

/**
 * One calm line per exercise: thumbnail + name + prescription, with a
 * standing "View" link to the how-to page. The reasoning, rank, and
 * citations live behind the row — tap to open "Why this pick".
 */
export function ExerciseRow({ exercise }: { exercise: ProtocolExercise }) {
  const [open, setOpen] = useState(false);
  const reduced = useReducedMotion();
  const panelId = useId();
  const evidence = exercise.referenceEvidence;
  const rank = parseRankDisplay(exercise.rankDisplay);
  const thumbnail = useExerciseThumbnail(exercise.exerciseId, exercise.thumbnail);

  return (
    <div className="transition-colors hover:bg-surface-muted/50">
      <div className="flex items-center px-4 py-3.5 sm:px-6">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls={panelId}
          className="group flex min-w-0 flex-1 items-center gap-3 text-left sm:gap-3.5"
        >
          <span className="relative flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border bg-surface-muted font-mono text-sm text-subtle sm:h-11 sm:w-11">
            {exercise.name.charAt(0)}
            {thumbnail && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={thumbnail}
                alt=""
                loading="lazy"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
                className="absolute inset-0 h-full w-full object-cover"
              />
            )}
          </span>
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-2 text-[0.95rem] font-medium text-ink">
              <span className="line-clamp-2 sm:line-clamp-1">{exercise.name}</span>
              {exercise.lowerTrustEvidence && (
                <span
                  title="Some supporting evidence is flagged lower-trust — details inside."
                  className="h-1.5 w-1.5 shrink-0 rounded-full bg-warning"
                />
              )}
            </span>
            <span className="mt-0.5 block text-[0.75rem] text-subtle">
              {exercise.targetLabel}
              {evidence.length > 0 && (
                <> · {evidence.length === 1 ? "1 study" : `${evidence.length} studies`}</>
              )}
            </span>
          </span>
          <span className="shrink-0 text-right">
            <span className="tnum block font-mono text-sm font-semibold text-ink">
              {exercise.prescription.display ?? "—"}
            </span>
            {exercise.prescription.rest && (
              <span className="tnum mt-0.5 block text-[0.7rem] text-subtle">
                {exercise.prescription.rest} rest
              </span>
            )}
          </span>
          <ChevronDown
            className={cn(
              "ml-2 h-4 w-4 shrink-0 text-subtle transition-transform duration-200 group-hover:text-muted sm:ml-3",
              open && "rotate-180",
            )}
          />
        </button>
        {exercise.exerciseId && (
          <Link
            href={`/exercises/${exercise.exerciseId}`}
            title={`How to perform ${exercise.name}`}
            className="ml-2 inline-flex h-8 shrink-0 items-center gap-1 rounded-lg border border-border bg-surface px-2 text-[0.74rem] font-medium text-muted transition-colors hover:border-accent hover:text-accent sm:ml-3 sm:px-2.5"
          >
            <ArrowUpRight className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">View</span>
          </Link>
        )}
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={panelId}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={
              reduced ? { duration: 0 } : { duration: 0.25, ease: [0.22, 1, 0.36, 1] }
            }
            className="overflow-hidden"
          >
            <div className="mx-5 mb-4 rounded-xl bg-surface-muted/60 p-4 sm:mx-6">
              <p className="font-mono text-[0.65rem] font-medium uppercase tracking-[0.16em] text-subtle">
                Why this pick
              </p>
              {exercise.selectionReason && (
                <p className="mt-2 text-[0.83rem] leading-relaxed text-muted">
                  {exercise.selectionReason}
                </p>
              )}
              {rank && (
                <p className="mt-1.5 text-[0.78rem] text-subtle">
                  Evidence rank{" "}
                  <span className="tnum font-medium text-muted">#{rank.rank}</span> of{" "}
                  <span className="tnum">{rank.total}</span>{" "}
                  {exercise.targetLabel.toLowerCase()} exercises in the catalog.
                </p>
              )}

              {evidence.length > 0 ? (
                <div className="mt-3 grid gap-2.5">
                  {evidence.map((item, i) => (
                    <EvidenceCard key={(item.pmid ?? "e") + i} item={item} />
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-[0.8rem] text-subtle">
                  No direct study match — selected on catalog ranking.
                </p>
              )}

              {exercise.lowerTrustEvidence && (
                <div className="mt-3">
                  <LowerTrustPill />
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
