"use client";

import { Cog } from "lucide-react";
import type { GenerateResponse } from "@/types/protocol";
import { Reveal } from "@/components/layout/reveal";
import { ProtocolHero } from "./protocol-hero";
import { SessionCard } from "./session-card";
import { EvidenceAppendix } from "./evidence-appendix";
import { WarningBanner } from "./warning-banner";

export function ProtocolResult({
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
  const hasNotes = data.usedFallback || data.warnings.length > 0;

  return (
    <div className="space-y-6">
      <Reveal>
        <ProtocolHero
          data={data}
          onRegenerate={onRegenerate}
          onTweak={onTweak}
          regenerating={regenerating}
        />
      </Reveal>

      {hasNotes && (
        <Reveal delay={0.05}>
          <div className="space-y-2.5">
            {data.usedFallback && (
              <div className="flex items-start gap-2.5 rounded-xl border border-border bg-surface px-4 py-3">
                <Cog className="mt-0.5 h-4 w-4 shrink-0 text-subtle" />
                <p className="text-[0.83rem] leading-relaxed text-muted">
                  Assembled by the deterministic evidence ranker — the AI planner was
                  unavailable or its output failed validation.
                  {onRegenerate && (
                    <>
                      {" "}
                      <button
                        onClick={onRegenerate}
                        disabled={regenerating}
                        className="font-medium text-accent transition-colors hover:text-accent-hover disabled:opacity-50"
                      >
                        Regenerate
                      </button>{" "}
                      to try the AI planner again.
                    </>
                  )}
                </p>
              </div>
            )}
            <WarningBanner warnings={data.warnings} />
          </div>
        </Reveal>
      )}

      <div className="space-y-5">
        {data.sessions.map((session, i) => (
          <Reveal key={session.sessionNumber + "-" + i} delay={0.08 + i * 0.05}>
            <SessionCard session={session} />
          </Reveal>
        ))}
      </div>

      {data.evidenceAppendix.length > 0 && (
        <Reveal delay={0.1}>
          <EvidenceAppendix items={data.evidenceAppendix} />
        </Reveal>
      )}
    </div>
  );
}
