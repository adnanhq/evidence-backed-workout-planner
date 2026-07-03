import Link from "next/link";
import { cn } from "@/lib/utils";
import { equipmentLabel, muscleLabel } from "@/lib/labels";
import { EvidenceBadge } from "@/components/evidence/evidence-badge";
import type { ExerciseSummary } from "@/types/exercise";

export function ExerciseCard({ ex }: { ex: ExerciseSummary }) {
  const conf = ex.confidenceScore ?? 0;
  return (
    <Link
      href={`/exercises/${ex.exerciseId}`}
      className="group flex h-full flex-col rounded-xl border border-border bg-surface p-4 shadow-xs transition-all duration-200 hover:border-border-strong hover:shadow-card"
    >
      {ex.thumbnail && (
        <div className="mb-3 overflow-hidden rounded-lg bg-surface-muted">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={ex.thumbnail}
            alt={ex.name}
            loading="lazy"
            className="h-32 w-full object-cover transition-transform duration-200 group-hover:scale-105"
          />
        </div>
      )}
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-[0.95rem] font-semibold leading-snug text-ink transition-colors group-hover:text-accent">
          {ex.name}
        </h3>
        {ex.bestTier && <EvidenceBadge tier={ex.bestTier} size="sm" />}
      </div>

      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {ex.primaryMuscles.slice(0, 3).map((m) => (
          <span
            key={m}
            className="rounded-md bg-surface-muted px-1.5 py-0.5 text-[0.7rem] text-muted"
          >
            {muscleLabel(m)}
          </span>
        ))}
      </div>

      <div className="mt-3.5 flex items-center gap-2">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-muted">
          <div
            className={cn(
              "h-full rounded-full",
              conf >= 0.66 ? "bg-accent" : conf >= 0.45 ? "bg-[#7fc8bd]" : "bg-border-strong",
            )}
            style={{ width: `${Math.round(conf * 100)}%` }}
          />
        </div>
        <span className="text-[0.68rem] capitalize text-subtle">
          {ex.confidenceLevel ?? "—"}
        </span>
      </div>

      <div className="mt-auto flex items-center justify-between pt-3 text-[0.74rem] text-subtle">
        <span className="capitalize">
          {ex.equipment.map(equipmentLabel)[0] ?? "—"}
          {ex.difficulty ? ` · ${ex.difficulty}` : ""}
        </span>
        <span>
          {ex.evidenceCount > 0
            ? `${ex.evidenceCount} ${ex.evidenceCount === 1 ? "study" : "studies"}`
            : "biomechanical"}
        </span>
      </div>
    </Link>
  );
}
