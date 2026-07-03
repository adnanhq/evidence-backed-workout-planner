"use client";

import { useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUpRight, BookOpen, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProtocolExercise } from "@/types/protocol";
import { CitationChip } from "@/components/evidence/citation-chip";
import { EvidenceCard } from "@/components/evidence/evidence-card";
import { LowerTrustPill } from "@/components/evidence/lower-trust-pill";

export function ExerciseRow({ exercise }: { exercise: ProtocolExercise }) {
  const [open, setOpen] = useState(false);
  const evidence = exercise.referenceEvidence;
  const hasEvidence = evidence.length > 0;

  return (
    <div className="px-4 py-4 transition-colors hover:bg-surface-muted/40 sm:px-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-surface-muted px-2 py-0.5 text-[0.7rem] font-medium text-muted">
              {exercise.targetLabel}
            </span>
            <h4 className="text-[0.98rem] font-semibold text-ink">{exercise.name}</h4>
            {exercise.rankDisplay && (
              <span
                title="Ranked by evidence + fit within this muscle"
                className="tnum rounded-md border border-border bg-surface px-1.5 py-0.5 text-[0.68rem] font-medium text-accent"
              >
                {exercise.rankDisplay}
              </span>
            )}
          </div>
          {exercise.selectionReason && (
            <p className="mt-1.5 text-[0.8rem] leading-relaxed text-subtle">
              {exercise.selectionReason}
            </p>
          )}
        </div>
        <div className="shrink-0 text-right">
          {exercise.prescription.display && (
            <div className="tnum font-mono text-sm font-semibold text-ink">
              {exercise.prescription.display}
            </div>
          )}
          {exercise.prescription.rest && (
            <div className="tnum text-[0.72rem] text-subtle">
              {exercise.prescription.rest} rest
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {hasEvidence ? (
          evidence.map((item, i) => (
            <CitationChip key={(item.pmid ?? "x") + i} item={item} />
          ))
        ) : (
          <span className="inline-flex items-center rounded-full border border-border bg-surface-muted px-2.5 py-1 text-[0.72rem] text-subtle">
            No direct study match — selected on catalog ranking
          </span>
        )}
        {exercise.lowerTrustEvidence && <LowerTrustPill />}
        <div className="ml-auto flex items-center gap-1">
          {exercise.exerciseId && (
            <Link
              href={`/exercises/${exercise.exerciseId}`}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[0.74rem] font-medium text-accent transition-colors hover:bg-accent-subtle"
            >
              <ArrowUpRight className="h-3.5 w-3.5" /> View exercise
            </Link>
          )}
          {hasEvidence && (
            <button
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[0.74rem] font-medium text-accent transition-colors hover:bg-accent-subtle"
            >
              <BookOpen className="h-3.5 w-3.5" /> Evidence ({evidence.length})
              <ChevronDown
                className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")}
              />
            </button>
          )}
        </div>
      </div>

      <AnimatePresence initial={false}>
        {open && hasEvidence && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-3 grid gap-2.5">
              {evidence.map((item, i) => (
                <EvidenceCard key={(item.pmid ?? "y") + i} item={item} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
