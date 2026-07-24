"use client";

import { Cog, Sparkles } from "lucide-react";
import { EXPERIENCE_LABELS, GOAL_LABELS, equipmentLabel } from "@/lib/labels";
import type { GenerateResponse } from "@/types/protocol";
import { ResultToolbar } from "./result-toolbar";

/**
 * The payoff moment: a single dark card that announces the generated
 * protocol — split, week at a glance, headline numbers, actions. Everything
 * else on the page hangs off this.
 */
export function ProtocolHero({
  data,
  onRegenerate,
  onTweak,
  regenerating,
}: {
  data: GenerateResponse;
  onRegenerate?: () => void;
  onTweak?: () => void;
  regenerating?: boolean;
}) {
  const req = data.request;
  const exerciseCount = data.sessions.reduce((n, s) => n + s.exercises.length, 0);
  const studyCount = data.evidenceAppendix.length;

  const recap = [
    GOAL_LABELS[req.goal] ?? req.goal,
    EXPERIENCE_LABELS[req.experience] ?? req.experience,
    req.equipment.length
      ? req.equipment.map(equipmentLabel).join(", ")
      : "Any equipment",
  ].join(" · ");

  return (
    <section className="relative overflow-hidden rounded-2xl bg-ink-surface shadow-on-dark">
      <div aria-hidden className="aurora absolute inset-0 opacity-70" />
      <div
        aria-hidden
        className="bg-grid-dark absolute inset-0 [mask-image:radial-gradient(85%_90%_at_25%_0%,black,transparent)]"
      />

      <div className="relative p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="flex items-center gap-2.5 font-mono text-[0.68rem] font-medium uppercase tracking-[0.18em] text-on-dark-subtle">
            <span className="relative flex h-2 w-2" aria-hidden>
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-on-dark opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-accent-on-dark" />
            </span>
            1-week protocol · ready
          </p>
          <span
            title={
              data.usedFallback
                ? "The AI planner was unavailable or failed validation, so this plan was assembled by the deterministic evidence ranker."
                : "Planned by AI from your evidence-ranked exercise candidates."
            }
            className="glass-dark inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[0.7rem] font-medium text-on-dark-muted"
          >
            {data.usedFallback ? (
              <>
                <Cog className="h-3 w-3" /> Deterministic build
              </>
            ) : (
              <>
                <Sparkles className="h-3 w-3 text-accent-on-dark" /> AI-planned
              </>
            )}
          </span>
        </div>

        <h1 className="mt-5 font-heading text-3xl font-semibold tracking-tight text-on-dark sm:text-4xl">
          {data.splitSummary ?? "Your protocol"}
        </h1>
        <p className="mt-2 text-sm text-on-dark-muted">{recap}</p>

        {data.sessions.length > 1 && (
          <nav aria-label="Jump to a session" className="mt-6 flex flex-wrap gap-2">
            {data.sessions.map((s) => (
              <a
                key={s.sessionNumber}
                href={`#session-${s.sessionNumber}`}
                className="glass-dark inline-flex max-w-60 items-baseline gap-2 rounded-full px-3.5 py-1.5 text-[0.78rem] transition-colors hover:bg-white/10"
              >
                <span className="tnum font-mono text-[0.68rem] text-accent-on-dark">
                  {String(s.sessionNumber).padStart(2, "0")}
                </span>
                <span className="truncate text-on-dark-muted">{s.splitLabel}</span>
              </a>
            ))}
          </nav>
        )}

        <div className="mt-7 flex flex-wrap items-end justify-between gap-x-8 gap-y-5 border-t border-on-dark-border pt-5">
          <div className="flex flex-wrap gap-x-8 gap-y-4">
            <Stat value={req.sessions} label="sessions / week" />
            <Stat value={req.sessionMinutes} label="min / session" />
            <Stat value={exerciseCount} label="exercises" />
            {studyCount > 0 && <Stat value={studyCount} label="studies cited" />}
          </div>
          <ResultToolbar
            data={data}
            onRegenerate={onRegenerate}
            onTweak={onTweak}
            regenerating={regenerating}
          />
        </div>
      </div>
    </section>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <div>
      <div className="tnum font-mono text-2xl font-medium text-on-dark">{value}</div>
      <div className="mt-1 text-[0.62rem] font-medium uppercase tracking-[0.14em] text-on-dark-subtle">
        {label}
      </div>
    </div>
  );
}
