import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal } from "@/components/layout/reveal";
import { buttonClasses } from "@/components/ui/button";
import { FootnoteBand, Sup } from "./footnote";

export function CtaBand() {
  return (
    <section className="relative isolate overflow-hidden bg-ink-surface text-on-dark">
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="aurora absolute inset-0" />
        <div className="bg-grid-dark absolute inset-0 opacity-50 [mask-image:radial-gradient(70%_70%_at_50%_30%,black,transparent)]" />
      </div>

      <div className="relative mx-auto w-full max-w-[var(--container-page)] px-5 py-28 sm:px-8 sm:py-36">
        <Reveal>
          <h2 className="max-w-[14ch] font-display text-display text-on-dark">
            Train on the record.
            <Sup n={1} targetId="fn-1" />
          </h2>
          <Link
            href="/build"
            className={buttonClasses("primary", "lg", "mt-12 shadow-glow-teal")}
          >
            Build your protocol <ArrowRight className="h-4 w-4" />
          </Link>
        </Reveal>

        <FootnoteBand
          tone="dark"
          className="mt-24"
          items={[
            {
              n: 1,
              id: "fn-1",
              label:
                "Every citation resolves to PubMed — 502 graded studies; 147 flagged for manual review and labeled as such.",
            },
          ]}
          aside="No opinions were consulted"
        />
      </div>
    </section>
  );
}
