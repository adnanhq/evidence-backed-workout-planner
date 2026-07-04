import type { Metadata } from "next";
import { Eyebrow, Section } from "@/components/layout/section";
import { ExerciseLibrary } from "@/components/exercises/exercise-library";

export const metadata: Metadata = {
  title: "Exercise library",
  description:
    "Browse 1,324 exercises, each scored for hypertrophy and strength and linked to the evidence behind it.",
};

export default function ExercisesPage() {
  return (
    <div className="pb-10">
      <Section className="pt-12 sm:pt-16">
        <div className="max-w-2xl">
          <Eyebrow>Library</Eyebrow>
          <h1 className="mt-3 font-heading text-[2.1rem] font-semibold leading-tight text-ink sm:text-[2.6rem]">
            1,324 exercises, ranked by evidence
          </h1>
          <p className="mt-4 text-base leading-relaxed text-muted">
            Browse the full catalog. Each exercise is scored for hypertrophy and
            strength, profiled for joint stress, and linked to the peer-reviewed studies
            behind it.
          </p>
        </div>
      </Section>
      <div className="mt-8">
        <ExerciseLibrary />
      </div>
    </div>
  );
}
