"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Section } from "@/components/layout/section";
import type {
  Experience,
  GenerateRequest,
  Goal,
  Joint,
  SplitTemplate,
} from "@/types/protocol";
import type { ApiError } from "@/lib/api";
import { useGenerateProtocol } from "@/lib/queries";
import {
  echoToRequest,
  loadProtocol,
  PROTOCOL_QUERY_KEY,
  saveProtocol,
} from "@/lib/protocol-store";
import { EXPERIENCE_BLURB, GOAL_BLURB } from "@/lib/labels";
import { FormField } from "./form-field";
import { Segmented } from "./segmented";
import { Stepper } from "./stepper";
import {
  EquipmentSelector,
  JointSelector,
  MuscleSelector,
  SplitSelect,
} from "./selectors";
import { RequestSummary } from "./request-summary";
import { LoadingProtocol } from "@/components/result/loading-protocol";
import { ProtocolErrorState } from "@/components/result/states";

const GOAL_OPTIONS = [
  { value: "hypertrophy", label: "Hypertrophy" },
  { value: "strength", label: "Strength" },
];
const EXPERIENCE_OPTIONS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

export function BuilderExperience() {
  const [goal, setGoal] = useState<Goal>("hypertrophy");
  const [muscles, setMuscles] = useState<string[]>([]);
  const [equipment, setEquipment] = useState<string[]>([
    "barbell",
    "dumbbell",
    "cable",
    "machine",
    "bodyweight",
  ]);
  const [experience, setExperience] = useState<Experience>("intermediate");
  const [sessions, setSessions] = useState(3);
  const [sessionMinutes, setSessionMinutes] = useState(60);
  const [perSessionOn, setPerSessionOn] = useState(false);
  const [perSession, setPerSession] = useState(4);
  const [avoidJoints, setAvoidJoints] = useState<string[]>([]);
  const [splitTemplate, setSplitTemplate] = useState<SplitTemplate>("auto");
  const [notes, setNotes] = useState("");

  const router = useRouter();
  const queryClient = useQueryClient();
  const gen = useGenerateProtocol();

  // Pre-fill from the last generated protocol so returning here to "Edit inputs"
  // keeps the previous selections intact.
  useEffect(() => {
    const stash = loadProtocol();
    if (!stash) return;
    const r = echoToRequest(stash.request);
    /* eslint-disable react-hooks/set-state-in-effect -- one-time prefill from the stored request; must run after mount to avoid an SSR/client hydration mismatch */
    setGoal(r.goal);
    setMuscles(r.muscles);
    setEquipment(r.equipment);
    setExperience(r.experience);
    setSessions(r.sessions);
    setSessionMinutes(r.sessionMinutes);
    if (r.exercisesPerSession != null) {
      setPerSessionOn(true);
      setPerSession(r.exercisesPerSession);
    }
    setAvoidJoints(r.avoidJoints);
    setSplitTemplate(r.splitTemplate);
    setNotes(r.notes ?? "");
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  const missing: string[] = [];
  if (muscles.length === 0) missing.push("at least one target muscle");
  if (equipment.length === 0) missing.push("at least one equipment type");
  const valid = missing.length === 0;

  function buildRequest(): GenerateRequest {
    return {
      goal,
      muscles,
      sessions,
      sessionMinutes,
      exercisesPerSession: perSessionOn ? perSession : null,
      equipment,
      experience,
      avoidJoints: avoidJoints as Joint[],
      notes,
      splitTemplate,
    };
  }

  function submit() {
    if (!valid) return;
    const request = buildRequest();
    gen.mutate(request, {
      onSuccess: (response) => {
        saveProtocol(request, response);
        queryClient.setQueryData(PROTOCOL_QUERY_KEY, response);
        router.push("/protocol");
      },
    });
  }

  // The generation can take 1–3 minutes; take over the builder area with a clear
  // loading state, then navigate to /protocol on success.
  if (gen.isPending) {
    return (
      <Section className="pb-6">
        <LoadingProtocol />
      </Section>
    );
  }

  return (
    <Section className="pb-6">
      <div className="grid gap-7 lg:grid-cols-[1fr_19rem]">
        {/* Form column */}
        <div className="space-y-5">
          <FormField title="Your goal" hint={GOAL_BLURB[goal]}>
            <Segmented
              options={GOAL_OPTIONS}
              value={goal}
              onChange={(v) => setGoal(v as Goal)}
            />
          </FormField>

          <FormField
            title="Target muscles"
            hint="Pick the muscles you want this week to prioritize."
            aside={
              muscles.length > 0 ? (
                <button
                  onClick={() => setMuscles([])}
                  className="text-xs font-medium text-accent hover:text-accent-hover"
                >
                  Clear ({muscles.length})
                </button>
              ) : null
            }
          >
            <MuscleSelector selected={muscles} onChange={setMuscles} />
          </FormField>

          <FormField
            title="Available equipment"
            hint="We only suggest exercises you can actually perform."
            aside={
              <span className="text-xs text-subtle">{equipment.length} selected</span>
            }
          >
            <EquipmentSelector selected={equipment} onChange={setEquipment} />
          </FormField>

          <FormField title="Experience" hint={EXPERIENCE_BLURB[experience]}>
            <Segmented
              options={EXPERIENCE_OPTIONS}
              value={experience}
              onChange={(v) => setExperience(v as Experience)}
            />
          </FormField>

          <FormField title="Your week" hint="How much you can train.">
            <div className="flex flex-wrap items-end gap-x-10 gap-y-4">
              <div>
                <label className="mb-1.5 block text-[0.8rem] font-medium text-muted">
                  Sessions / week
                </label>
                <Stepper value={sessions} onChange={setSessions} min={1} max={7} />
              </div>
              <div>
                <label className="mb-1.5 block text-[0.8rem] font-medium text-muted">
                  Minutes / session
                </label>
                <Stepper
                  value={sessionMinutes}
                  onChange={setSessionMinutes}
                  min={20}
                  max={120}
                  step={5}
                />
              </div>
            </div>
            <div className="mt-5 flex items-center justify-between gap-3 rounded-lg bg-surface-muted px-3.5 py-3">
              <div>
                <p className="text-sm font-medium text-ink">Exercises per session</p>
                <p className="text-[0.78rem] text-subtle">
                  Auto picks a sensible count from your time budget.
                </p>
              </div>
              {perSessionOn ? (
                <div className="flex items-center gap-2">
                  <Stepper
                    value={perSession}
                    onChange={setPerSession}
                    min={1}
                    max={8}
                  />
                  <button
                    onClick={() => setPerSessionOn(false)}
                    className="text-xs font-medium text-accent hover:text-accent-hover"
                  >
                    Auto
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setPerSessionOn(true)}
                  className="shrink-0 rounded-md border border-border-strong bg-surface px-3 py-1.5 text-sm font-medium text-muted hover:border-accent hover:text-accent"
                >
                  Set manually
                </button>
              )}
            </div>
          </FormField>

          <FormField title="Weekly split" hint="How your sessions are organized.">
            <SplitSelect value={splitTemplate} onChange={(v) => setSplitTemplate(v as SplitTemplate)} />
          </FormField>

          <FormField
            title="Joints to ease load on"
            hint="Optional — we'll down-rank exercises that stress these joints."
          >
            <JointSelector selected={avoidJoints} onChange={setAvoidJoints} />
          </FormField>

          <FormField title="Notes" hint="Optional — anything else for the planner.">
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="e.g. tweaky left shoulder, prefer machines later in the week"
              className="w-full resize-none rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm text-ink placeholder:text-subtle focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
          </FormField>
        </div>

        {/* Sticky summary */}
        <div className="lg:sticky lg:top-20 lg:self-start">
          <RequestSummary
            state={{
              goal,
              muscles,
              equipment,
              sessions,
              sessionMinutes,
              splitTemplate,
              experience,
            }}
            valid={valid}
            missing={missing}
            pending={gen.isPending}
            onGenerate={submit}
          />
        </div>
      </div>

      {gen.isError && (
        <div className="mt-8">
          <ProtocolErrorState
            message={(gen.error as ApiError)?.message ?? "Something went wrong."}
            onRetry={submit}
            retrying={gen.isPending}
          />
        </div>
      )}
    </Section>
  );
}
