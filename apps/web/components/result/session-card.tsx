import { muscleLabel } from "@/lib/labels";
import type { ProtocolSession } from "@/types/protocol";
import { ExerciseRow } from "./exercise-row";

export function SessionCard({ session }: { session: ProtocolSession }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
      <div className="border-b border-border bg-surface-muted/60 px-4 py-3.5 sm:px-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="tnum rounded-md bg-accent px-2 py-0.5 text-xs font-semibold text-accent-fg">
              Session {session.sessionNumber}
            </span>
            <h3 className="font-display text-lg font-medium text-ink">
              {session.splitLabel}
            </h3>
          </div>
          <div className="hidden flex-wrap justify-end gap-1.5 sm:flex">
            {session.targetMuscles.map((m) => (
              <span
                key={m}
                className="rounded-full border border-border px-2 py-0.5 text-[0.7rem] text-muted"
              >
                {muscleLabel(m)}
              </span>
            ))}
          </div>
        </div>
        {session.focus && <p className="mt-1 text-[0.8rem] text-subtle">{session.focus}</p>}
      </div>
      <div className="divide-y divide-border">
        {session.exercises.map((exercise, i) => (
          <ExerciseRow key={exercise.exerciseId + i} exercise={exercise} />
        ))}
      </div>
    </div>
  );
}
