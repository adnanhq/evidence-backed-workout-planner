"use client";

import {
  EQUIPMENT_PRESETS,
  JOINT_LABELS,
  MUSCLE_REGIONS,
  SPLIT_BLURB,
  SPLIT_LABELS,
  equipmentLabel,
  muscleLabel,
} from "@/lib/labels";
import { useTaxonomies } from "@/lib/queries";
import { Chip } from "./chip";

const EQUIPMENT_CHOICES = [
  "barbell",
  "dumbbell",
  "cable",
  "machine",
  "bodyweight",
  "kettlebell",
  "ez_bar",
  "resistance_band",
  "medicine_ball",
  "stability_ball",
  "foam_roller",
];

const JOINT_CHOICES = [
  "neck",
  "shoulder",
  "elbow",
  "wrist",
  "spine",
  "hip",
  "knee",
  "ankle",
];

const SPLIT_CHOICES = ["auto", "full_body", "push_pull", "push_pull_legs", "upper_lower"];

function toggle(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export function MuscleSelector({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  // Only offer muscles the engine can actually target (primary movers per
  // /api/taxonomies); region groupings stay local for layout.
  const { data: taxonomies } = useTaxonomies();
  const allowed = new Set(taxonomies.muscleGroups);
  const regions = MUSCLE_REGIONS.map((region) => ({
    ...region,
    muscles: region.muscles.filter((m) => allowed.has(m)),
  })).filter((region) => region.muscles.length > 0);

  return (
    <div className="space-y-4">
      {regions.map((region) => (
        <div key={region.name}>
          <p className="mb-2 text-[0.72rem] font-semibold uppercase tracking-[0.1em] text-subtle">
            {region.name}
          </p>
          <div className="flex flex-wrap gap-2">
            {region.muscles.map((m) => (
              <Chip
                key={m}
                selected={selected.includes(m)}
                onClick={() => onChange(toggle(selected, m))}
              >
                {muscleLabel(m)}
              </Chip>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function EquipmentSelector({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        {Object.entries(EQUIPMENT_PRESETS).map(([name, list]) => (
          <button
            key={name}
            type="button"
            onClick={() => onChange(list)}
            className="rounded-full border border-dashed border-border-strong px-3 py-1 text-[0.78rem] font-medium text-muted transition-colors hover:border-accent hover:text-accent"
          >
            {name}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {EQUIPMENT_CHOICES.map((e) => (
          <Chip
            key={e}
            selected={selected.includes(e)}
            onClick={() => onChange(toggle(selected, e))}
          >
            {equipmentLabel(e)}
          </Chip>
        ))}
      </div>
    </div>
  );
}

export function JointSelector({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {JOINT_CHOICES.map((j) => (
        <Chip
          key={j}
          selected={selected.includes(j)}
          onClick={() => onChange(toggle(selected, j))}
        >
          {JOINT_LABELS[j]}
        </Chip>
      ))}
    </div>
  );
}

export function SplitSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {SPLIT_CHOICES.map((s) => (
          <Chip key={s} selected={value === s} onClick={() => onChange(s)}>
            {SPLIT_LABELS[s]}
          </Chip>
        ))}
      </div>
      <p className="mt-2.5 text-[0.82rem] text-subtle">{SPLIT_BLURB[value]}</p>
    </div>
  );
}
