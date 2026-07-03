import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Section } from "@/components/layout/section";
import { Reveal } from "@/components/layout/reveal";
import { buttonClasses } from "@/components/ui/button";

export function CtaBand() {
  return (
    <Section className="py-20">
      <Reveal>
        <div className="relative isolate overflow-hidden rounded-2xl bg-ink-surface px-6 py-16 text-center text-on-dark shadow-on-dark sm:px-12">
          <div aria-hidden className="pointer-events-none absolute inset-0">
            <div className="aurora absolute inset-0" />
            <div className="bg-grid-dark absolute inset-0 opacity-50 [mask-image:radial-gradient(60%_60%_at_50%_50%,black,transparent)]" />
          </div>
          <div className="relative">
            <h2 className="mx-auto max-w-2xl font-display text-3xl font-semibold leading-tight text-on-dark sm:text-[2.6rem]">
              Stop guessing. Start training on evidence.
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-base leading-relaxed text-on-dark-muted">
              Build a weekly protocol where every set is traceable to the research —
              in under a minute.
            </p>
            <Link
              href="/build"
              className={buttonClasses("primary", "lg", "mt-8 shadow-glow-teal")}
            >
              Build your protocol <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </Reveal>
    </Section>
  );
}
