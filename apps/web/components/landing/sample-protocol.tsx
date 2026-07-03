import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Eyebrow, Section } from "@/components/layout/section";
import { Reveal } from "@/components/layout/reveal";
import { SessionCard } from "@/components/result/session-card";
import { EvidenceCard } from "@/components/evidence/evidence-card";
import { buttonClasses } from "@/components/ui/button";
import { DEMO_PROTOCOL } from "@/lib/demo-data";

export function SampleProtocol() {
  const session = DEMO_PROTOCOL.sessions[0];
  const appendix = DEMO_PROTOCOL.evidenceAppendix.slice(0, 2);

  return (
    <Section className="py-24 sm:py-28">
      <div className="rounded-2xl border border-border bg-surface-muted/40 p-6 shadow-card sm:p-10">
        <Reveal>
          <div className="max-w-2xl">
            <Eyebrow>A real protocol</Eyebrow>
            <h2 className="mt-3 font-display text-3xl font-semibold leading-tight text-ink sm:text-[2.5rem]">
              See exactly what you get
            </h2>
            <p className="mt-3 text-[0.98rem] leading-relaxed text-muted">
              A live session from a hypertrophy protocol. Open any exercise&apos;s
              evidence and click straight through to PubMed — try it.
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.08}>
          <div className="mt-8 grid gap-5 lg:grid-cols-[1.45fr_1fr]">
            <SessionCard session={session} />
            <div>
              <p className="text-[0.76rem] font-semibold uppercase tracking-[0.1em] text-subtle">
                From the evidence appendix
              </p>
              <div className="mt-3 space-y-2.5">
                {appendix.map((item, i) => (
                  <EvidenceCard key={i} item={item} />
                ))}
              </div>
              <Link href="/build" className={buttonClasses("primary", "md", "mt-6")}>
                Build yours <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
