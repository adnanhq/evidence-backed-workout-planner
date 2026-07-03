"use client";

import { Loader2, Sparkles } from "lucide-react";
import { buttonClasses } from "@/components/ui/button";
import {
  EXPERIENCE_LABELS,
  GOAL_LABELS,
  SPLIT_LABELS,
  equipmentLabel,
  muscleLabel,
} from "@/lib/labels";

export interface SummaryState {
  goal: string;
  muscles: string[];
  equipment: string[];
  sessions: number;
  sessionMinutes: number;
  splitTemplate: string;
  experience: string;
}

export function RequestSummary({
  state,
  valid,
  missing,
  pending,
  onGenerate,
}: {
  state: SummaryState;
  valid: boolean;
  missing: string[];
  pending: boolean;
  onGenerate: () => void;
}) {
  const rows = [
    { label: "Goal", value: GOAL_LABELS[state.goal] ?? state.goal },
    {
      label: "Muscles",
      value: state.muscles.length ? state.muscles.map(muscleLabel).join(", ") : "—",
    },
    {
      label: "Equipment",
      value: state.equipment.length
        ? state.equipment.length <= 2
          ? state.equipment.map(equipmentLabel).join(", ")
          : `${state.equipment.length} selected`
        : "—",
    },
    {
      label: "Schedule",
      value: `${state.sessions}× / week · ${state.sessionMinutes} min`,
    },
    { label: "Split", value: SPLIT_LABELS[state.splitTemplate] ?? state.splitTemplate },
    { label: "Experience", value: EXPERIENCE_LABELS[state.experience] ?? state.experience },
  ];

  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
      <h3 className="font-display text-lg font-medium text-ink">Your request</h3>
      <dl className="mt-4 space-y-2.5">
        {rows.map((r) => (
          <div
            key={r.label}
            className="flex items-baseline justify-between gap-3 text-sm"
          >
            <dt className="shrink-0 text-subtle">{r.label}</dt>
            <dd className="text-right font-medium text-ink">{r.value}</dd>
          </div>
        ))}
      </dl>

      {missing.length > 0 && (
        <div className="mt-4 rounded-lg bg-surface-muted p-3">
          <p className="text-[0.78rem] font-medium text-muted">To generate, add:</p>
          <ul className="mt-1.5 space-y-1">
            {missing.map((m) => (
              <li
                key={m}
                className="flex items-center gap-1.5 text-[0.8rem] text-subtle"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-warning" />
                {m}
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        onClick={onGenerate}
        disabled={!valid || pending}
        className={buttonClasses("primary", "md", "mt-5 w-full")}
      >
        {pending ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" /> Building…
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" /> Generate protocol
          </>
        )}
      </button>
      <p className="mt-2.5 text-center text-[0.72rem] text-subtle">
        Built from 1,324 exercises &amp; 502 peer-reviewed studies
      </p>
    </div>
  );
}
