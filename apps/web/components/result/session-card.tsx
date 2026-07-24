import { muscleLabel } from "@/lib/labels";
import type { ProtocolSession } from "@/types/protocol";
import { ExerciseRow } from "./exercise-row";

export function SessionCard({ session }: { session: ProtocolSession }) {
  return (
    <article
      id={`session-${session.sessionNumber}`}
      className="scroll-mt-28 overflow-hidden rounded-2xl border border-border bg-surface shadow-card"
    >
      {/* Teal band with the protocol card's grid + sheen texture — ties each
          session to it and separates it hard from the rows. A shade lighter
          than that card so the card stays the page's anchor. */}
      <header className="relative overflow-hidden bg-teal-surface-2 px-5 py-4 sm:px-6">
        <div aria-hidden className="teal-sheen absolute inset-0 opacity-80" />
        <div
          aria-hidden
          className="bg-grid-dark absolute inset-0 [mask-image:radial-gradient(130%_160%_at_20%_0%,black,transparent)]"
        />
        <div className="relative">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <div className="flex min-w-0 items-baseline gap-3">
              <span className="tnum shrink-0 font-mono text-[0.8rem] font-medium text-accent-on-dark">
                {String(session.sessionNumber).padStart(2, "0")}
              </span>
              <h2 className="truncate font-heading text-lg font-semibold tracking-tight text-on-teal">
                {session.splitLabel}
              </h2>
            </div>
            <p className="hidden text-[0.75rem] text-on-teal-muted sm:block">
              {session.targetMuscles.map(muscleLabel).join(" · ")}
            </p>
          </div>
          {session.focus && (
            <p className="mt-0.5 pl-8 text-[0.78rem] text-on-teal-subtle">{session.focus}</p>
          )}
        </div>
      </header>
      <div className="divide-y divide-border">
        {session.exercises.map((exercise, i) => (
          <ExerciseRow key={exercise.exerciseId + i} exercise={exercise} />
        ))}
      </div>
    </article>
  );
}
