import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal } from "@/components/layout/reveal";
import { SessionCard } from "@/components/result/session-card";
import { EvidenceCard } from "@/components/evidence/evidence-card";
import { buttonClasses } from "@/components/ui/button";
import { DEMO_PROTOCOL } from "@/lib/demo-data";
import { LedgerHeading } from "./ledger";

export function SampleProtocol() {
  const session = DEMO_PROTOCOL.sessions[0];
  const appendix = DEMO_PROTOCOL.evidenceAppendix.slice(0, 2);

  return (
    <section id="sample" className="relative scroll-mt-16 py-24 sm:py-32">
      {/* Faint specimen grid behind the live demo */}
      <div
        aria-hidden
        className="bg-grid pointer-events-none absolute inset-0 opacity-50 [mask-image:radial-gradient(70%_60%_at_50%_45%,black,transparent)]"
      />
      <div className="relative mx-auto w-full max-w-[var(--container-page)] px-5 sm:px-8">
        <Reveal>
          <LedgerHeading index="03" label="A real protocol" title="This is the artifact.">
            <p>
              A live session from a hypertrophy protocol. Open the evidence on
              any exercise — every citation resolves to PubMed.
            </p>
          </LedgerHeading>
        </Reveal>

        <Reveal delay={0.08}>
          <div className="mt-12 grid gap-8 lg:grid-cols-[1.45fr_1fr]">
            <SessionCard session={session} />
            <div>
              <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-subtle">
                From the evidence appendix
              </p>
              <div className="mt-4 space-y-2.5">
                {appendix.map((item, i) => (
                  <EvidenceCard key={i} item={item} />
                ))}
              </div>
              <Link href="/build" className={buttonClasses("primary", "md", "mt-8")}>
                Build yours <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
