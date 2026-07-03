"use client";

import Link from "next/link";
import { ArrowLeft, Check, Loader2 } from "lucide-react";
import { Section } from "@/components/layout/section";
import { useExercise } from "@/lib/queries";
import { GOAL_LABELS, JOINT_LABELS, equipmentLabel, muscleLabel } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { EvidenceCard } from "@/components/evidence/evidence-card";
import type { EvidenceItem, EvidenceTier, TrustLabel } from "@/types/protocol";

const JOINT_ORDER = [
  "neck",
  "shoulder",
  "elbow",
  "wrist",
  "spine",
  "hip",
  "knee",
  "ankle",
];

export function ExerciseDetailView({ id }: { id: string }) {
  const { data: ex, isLoading, isError } = useExercise(id);

  if (isLoading) {
    return (
      <Section className="py-24">
        <div className="flex items-center gap-2 text-muted">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading exercise…
        </div>
      </Section>
    );
  }

  if (isError || !ex) {
    return (
      <Section className="py-24">
        <p className="text-muted">We couldn&apos;t find that exercise.</p>
        <Link href="/exercises" className="mt-2 inline-block font-medium text-accent">
          ← Back to the library
        </Link>
      </Section>
    );
  }

  const studyItems: EvidenceItem[] = ex.evidence.studies.map((s) => ({
    pmid: s.pmid,
    title: s.title,
    year: s.year,
    tier: s.tier as EvidenceTier,
    trustLabel: (s.trustLabel === "lower-trust" ? "lower-trust" : "standard") as TrustLabel,
    snippet: s.snippet,
    url: s.url,
  }));

  const meta = [ex.mechanic, ex.force, ex.difficulty, ex.category].filter(Boolean);

  return (
    <Section className="py-10 sm:py-14">
      <Link
        href="/exercises"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-muted transition-colors hover:text-accent"
      >
        <ArrowLeft className="h-4 w-4" /> Library
      </Link>

      <header className="mt-5 border-b border-border pb-6">
        <h1 className="font-display text-3xl font-semibold leading-tight text-ink sm:text-4xl">
          {ex.name}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {ex.primaryMuscles.map((m) => (
            <span
              key={m}
              className="rounded-full bg-accent-subtle px-2.5 py-0.5 text-xs font-medium text-accent"
            >
              {muscleLabel(m)}
            </span>
          ))}
          {ex.secondaryMuscles.map((m) => (
            <span
              key={m}
              className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted"
            >
              {muscleLabel(m)}
            </span>
          ))}
        </div>
        <p className="mt-3 text-sm capitalize text-subtle">
          {meta.join(" · ")}
          {ex.equipment.length
            ? ` · ${ex.equipment.map(equipmentLabel).join(", ")}`
            : ""}
        </p>
      </header>

      <div className="mt-8 grid gap-8 lg:grid-cols-[1.4fr_1fr]">
        {/* Main */}
        <main className="space-y-8">
          {ex.gif && (
            <figure className="overflow-hidden rounded-xl border border-border bg-surface-muted">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={ex.gif}
                alt={`${ex.name} demonstration`}
                className="mx-auto w-full max-w-md"
                loading="lazy"
              />
            </figure>
          )}
          <div>
            <h2 className="font-display text-xl font-medium text-ink">Goal fit</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {Object.entries(ex.goalProfiles).map(([goal, profile]) => (
                <div
                  key={goal}
                  className="rounded-xl border border-border bg-surface p-4 shadow-xs"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium text-ink">
                      {GOAL_LABELS[goal] ?? goal}
                    </h3>
                    {profile.recommended && (
                      <span className="inline-flex items-center gap-1 text-[0.72rem] font-medium text-success">
                        <Check className="h-3.5 w-3.5" /> Recommended
                      </span>
                    )}
                  </div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-muted">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${Math.round((profile.score ?? 0) * 100)}%` }}
                    />
                  </div>
                  {profile.rationale?.length > 0 && (
                    <ul className="mt-3 space-y-1.5">
                      {profile.rationale.slice(0, 3).map((r, i) => (
                        <li key={i} className="text-[0.82rem] leading-relaxed text-muted">
                          {r}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>

          {ex.instructions.length > 0 && (
            <div>
              <h2 className="font-display text-xl font-medium text-ink">How to perform</h2>
              <ol className="mt-4 space-y-3">
                {ex.instructions.map((step, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="tnum flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-muted text-[0.72rem] font-semibold text-muted">
                      {i + 1}
                    </span>
                    <p className="text-[0.92rem] leading-relaxed text-muted">{step}</p>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </main>

        {/* Sidebar */}
        <aside className="space-y-6">
          <div className="rounded-xl border border-border bg-surface p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-lg font-medium text-ink">Evidence</h2>
              <span className="text-xs capitalize text-subtle">
                {ex.evidence.confidenceLevel ?? "—"} confidence
              </span>
            </div>
            {studyItems.length > 0 ? (
              <div className="mt-4 space-y-2.5">
                {studyItems.map((item, i) => (
                  <EvidenceCard key={(item.pmid ?? "s") + i} item={item} />
                ))}
              </div>
            ) : (
              <div className="mt-3">
                <p className="text-sm text-muted">
                  No direct exercise-name study match. Included on biomechanical
                  reasoning:
                </p>
                <ul className="mt-2 space-y-1.5">
                  {ex.evidence.fallbackBasis.map((b, i) => (
                    <li
                      key={i}
                      className="flex gap-2 text-[0.82rem] leading-relaxed text-muted"
                    >
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" />
                      {b}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {ex.jointStress?.profile && (
            <div className="rounded-xl border border-border bg-surface p-5 shadow-xs">
              <h2 className="font-display text-lg font-medium text-ink">Joint stress</h2>
              <div className="mt-4 space-y-2.5">
                {JOINT_ORDER.filter((j) => ex.jointStress.profile?.[j]).map((j) => {
                  const entry = ex.jointStress.profile![j];
                  return (
                    <div key={j} className="flex items-center gap-3">
                      <span className="w-20 shrink-0 text-[0.8rem] text-muted">
                        {JOINT_LABELS[j]}
                      </span>
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-muted">
                        <div
                          className={cn("h-full rounded-full", jointColor(entry.label))}
                          style={{ width: `${Math.min(100, (entry.score / 3) * 100)}%` }}
                        />
                      </div>
                      <span className="w-16 shrink-0 text-right text-[0.72rem] capitalize text-subtle">
                        {entry.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </aside>
      </div>
    </Section>
  );
}

function jointColor(label: string): string {
  switch (label) {
    case "high":
      return "bg-danger/70";
    case "moderate":
      return "bg-warning";
    case "low":
      return "bg-[#7fc8bd]";
    default:
      return "bg-border-strong";
  }
}
