"use client";

import { useState } from "react";
import { Check, Copy, Download, Loader2, RefreshCw, SlidersHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import type { GenerateResponse } from "@/types/protocol";

const BASE =
  "inline-flex h-9 select-none items-center gap-1.5 rounded-lg px-3.5 text-[0.8rem] font-medium transition-colors duration-200 ease-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-on-dark/50 disabled:pointer-events-none disabled:opacity-50";
const GLASS = "glass-teal text-on-teal hover:bg-white/20";

/** Compact action row rendered on the teal protocol hero. */
export function ResultToolbar({
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
  const markdown = data.markdown;
  const [copied, setCopied] = useState(false);
  const [pdfStatus, setPdfStatus] = useState<"idle" | "generating" | "done">("idle");

  async function copy() {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable */
    }
  }

  async function downloadPdf() {
    setPdfStatus("generating");
    try {
      const { downloadProtocolPdf } = await import("@/components/result/protocol-pdf");
      await downloadProtocolPdf(data);
      setPdfStatus("done");
      setTimeout(() => setPdfStatus("idle"), 2000);
    } catch (err) {
      console.error(err);
      setPdfStatus("idle");
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        onClick={downloadPdf}
        disabled={pdfStatus === "generating"}
        className={cn(BASE, "bg-on-teal text-teal-surface hover:bg-white")}
      >
        {pdfStatus === "done" ? (
          <>
            <Check className="h-4 w-4" /> Saved
          </>
        ) : pdfStatus === "generating" ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" /> Generating…
          </>
        ) : (
          <>
            <Download className="h-4 w-4" /> Download PDF
          </>
        )}
      </button>
      {markdown && (
        <button onClick={copy} className={cn(BASE, GLASS)}>
          {copied ? (
            <>
              <Check className="h-4 w-4 text-accent-on-dark" /> Copied
            </>
          ) : (
            <>
              <Copy className="h-4 w-4" /> Copy Markdown
            </>
          )}
        </button>
      )}
      {onTweak && (
        <button onClick={onTweak} className={cn(BASE, GLASS)}>
          <SlidersHorizontal className="h-4 w-4" /> Edit inputs
        </button>
      )}
      {onRegenerate && (
        <button onClick={onRegenerate} disabled={regenerating} className={cn(BASE, GLASS)}>
          <RefreshCw className={cn("h-4 w-4", regenerating && "animate-spin")} />
          Regenerate
        </button>
      )}
    </div>
  );
}
