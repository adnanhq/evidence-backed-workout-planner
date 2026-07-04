"use client";

import { useState } from "react";
import { LayoutList, FileText, Sparkles, Cog } from "lucide-react";
import { cn } from "@/lib/utils";
import { protocolRecapLine } from "@/lib/labels";
import type { GenerateResponse } from "@/types/protocol";
import { SessionCard } from "./session-card";
import { EvidenceAppendix } from "./evidence-appendix";
import { WarningBanner } from "./warning-banner";
import { ResultToolbar } from "./result-toolbar";
import { MarkdownView } from "./markdown-view";

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
  const [tab, setTab] = useState<"protocol" | "markdown">("protocol");
  const recap = protocolRecapLine(data);

  const hasMarkdown = Boolean(data.markdown);

  return (
    <div>
      <header className="flex flex-col gap-4 border-b border-border pb-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className="font-display text-2xl font-semibold text-ink">
                Your 1-week protocol
              </h2>
              {data.splitSummary && (
                <span className="rounded-full bg-accent-subtle px-2.5 py-0.5 text-xs font-medium text-accent">
                  {data.splitSummary}
                </span>
              )}
            </div>
            <p className="mt-1.5 text-sm text-muted">{recap}</p>
            {!data.usedFallback && (
              <div className="mt-2">
                <span className="inline-flex items-center gap-1.5 text-[0.76rem] text-subtle">
                  <Sparkles className="h-3.5 w-3.5 text-accent" />
                  AI-planned from your evidence-ranked candidates
                </span>
              </div>
            )}
          </div>
          <ResultToolbar
            data={data}
            onRegenerate={onRegenerate}
            onTweak={onTweak}
            regenerating={regenerating}
          />
        </div>

        {hasMarkdown && (
          <div className="flex w-fit items-center gap-1 rounded-lg border border-border bg-surface-muted p-1">
            <TabButton active={tab === "protocol"} onClick={() => setTab("protocol")}>
              <LayoutList className="h-4 w-4" /> Protocol
            </TabButton>
            <TabButton active={tab === "markdown"} onClick={() => setTab("markdown")}>
              <FileText className="h-4 w-4" /> Markdown
            </TabButton>
          </div>
        )}
      </header>

      {data.usedFallback && (
        <div className="mt-6 rounded-lg border border-[#f0dcb8] bg-warning-subtle px-4 py-3.5">
          <div className="flex gap-2.5">
            <Cog className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
            <div>
              <p className="text-sm font-medium text-warning">
                This plan was generated deterministically
              </p>
              <p className="mt-1 text-[0.83rem] leading-relaxed text-[#7a5518]">
                The AI planner was unavailable or its output failed validation, so exercises
                were selected by the evidence-ranked fallback. Regenerate to try the AI
                planner again.
              </p>
            </div>
          </div>
        </div>
      )}

      {tab === "protocol" ? (
        <div className="mt-6 space-y-6">
          <WarningBanner warnings={data.warnings} />
          <div className="space-y-4">
            {data.sessions.map((session, i) => (
              <SessionCard key={session.sessionNumber + "-" + i} session={session} />
            ))}
          </div>
          {data.evidenceAppendix.length > 0 && (
            <div className="border-t border-border pt-8">
              <EvidenceAppendix items={data.evidenceAppendix} />
            </div>
          )}
        </div>
      ) : (
        <div className="mt-6">
          <MarkdownView markdown={data.markdown} />
        </div>
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-surface text-ink shadow-xs" : "text-muted hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}
