import type { Metadata } from "next";
import { Eyebrow, Section } from "@/components/layout/section";
import { BuilderExperience } from "@/components/builder/builder-experience";

export const metadata: Metadata = {
  title: "Build a protocol",
  description:
    "Build an evidence-based weekly training protocol — every exercise ranked and cited to PubMed.",
};

export default function BuildPage() {
  return (
    <div className="pb-10">
      <Section className="pt-12 sm:pt-16">
        <div className="max-w-2xl">
          <Eyebrow>Protocol builder</Eyebrow>
          <h1 className="mt-3 font-heading text-[2.1rem] font-semibold leading-tight text-ink sm:text-[2.6rem]">
            Build your evidence-based week
          </h1>
          <p className="mt-4 text-base leading-relaxed text-muted">
            Tell us your goal, muscles, and equipment. We filter 1,324 exercises, retrieve
            the matching studies, and let the planner lay out your week — every pick
            cited to the science behind it.
          </p>
        </div>
      </Section>
      <div className="mt-8">
        <BuilderExperience />
      </div>
    </div>
  );
}
