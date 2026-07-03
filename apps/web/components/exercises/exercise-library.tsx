"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Loader2, Search } from "lucide-react";
import { Section } from "@/components/layout/section";
import { useExercises, useTaxonomies } from "@/lib/queries";
import { EQUIPMENT_LABELS, GOAL_LABELS, muscleLabel } from "@/lib/labels";
import { cn } from "@/lib/utils";
import { ExerciseCard } from "./exercise-card";

const EQUIPMENT = [
  "barbell",
  "dumbbell",
  "cable",
  "machine",
  "bodyweight",
  "kettlebell",
  "ez_bar",
  "resistance_band",
];
const PAGE_SIZE = 24;

export function ExerciseLibrary() {
  const [q, setQ] = useState("");
  const [muscle, setMuscle] = useState("");
  const [equipment, setEquipment] = useState("");
  const [goal, setGoal] = useState("");
  const [page, setPage] = useState(1);

  // Muscle options come from the engine's taxonomy (primary movers only) so the
  // dropdown always matches what the API can actually filter on.
  const { data: taxonomies } = useTaxonomies();
  const muscles = taxonomies.muscleGroups;

  const { data, isFetching, isError } = useExercises({
    q,
    muscle,
    equipment,
    goal,
    page,
    pageSize: PAGE_SIZE,
  });

  function reset<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v);
      setPage(1);
    };
  }

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <Section>
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[14rem] flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
          <input
            value={q}
            onChange={(e) => reset(setQ)(e.target.value)}
            placeholder="Search exercises…"
            className="h-10 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-ink placeholder:text-subtle focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
        <FilterSelect label="Muscle" value={muscle} onChange={reset(setMuscle)}>
          <option value="">All muscles</option>
          {muscles.map((m) => (
            <option key={m} value={m}>
              {muscleLabel(m)}
            </option>
          ))}
        </FilterSelect>
        <FilterSelect label="Equipment" value={equipment} onChange={reset(setEquipment)}>
          <option value="">All equipment</option>
          {EQUIPMENT.map((e) => (
            <option key={e} value={e}>
              {EQUIPMENT_LABELS[e]}
            </option>
          ))}
        </FilterSelect>
        <FilterSelect label="Goal" value={goal} onChange={reset(setGoal)}>
          <option value="">Any goal</option>
          {Object.entries(GOAL_LABELS).map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </FilterSelect>
      </div>

      <div className="mt-4 flex items-center gap-2 text-sm text-muted">
        {isFetching ? (
          <>
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…
          </>
        ) : (
          <span className="tnum">{total.toLocaleString()} exercises</span>
        )}
      </div>

      {isError ? (
        <p className="mt-10 rounded-xl border border-border bg-surface p-8 text-center text-sm text-muted">
          Couldn&apos;t load the library. Make sure the engine is running.
        </p>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {(data?.items ?? []).map((ex) => (
            <ExerciseCard key={ex.exerciseId} ex={ex} />
          ))}
        </div>
      )}

      {total > PAGE_SIZE && (
        <div className="mt-8 flex items-center justify-center gap-4">
          <PageButton
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft className="h-4 w-4" /> Prev
          </PageButton>
          <span className="tnum text-sm text-muted">
            Page {page} of {totalPages}
          </span>
          <PageButton
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next <ChevronRight className="h-4 w-4" />
          </PageButton>
        </div>
      )}
    </Section>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <select
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-10 rounded-lg border border-border bg-surface px-3 text-sm text-ink focus:border-accent focus:outline-none"
    >
      {children}
    </select>
  );
}

function PageButton({
  children,
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-3.5 py-2 text-sm font-medium text-ink transition-colors hover:border-accent hover:text-accent disabled:pointer-events-none disabled:opacity-40",
      )}
    >
      {children}
    </button>
  );
}
