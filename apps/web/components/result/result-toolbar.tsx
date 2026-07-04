"use client";

import { useState } from "react";
import { Check, Copy, Download, Loader2, RefreshCw, SlidersHorizontal } from "lucide-react";
import { buttonClasses } from "@/components/ui/button";
import type { GenerateResponse } from "@/types/protocol";

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
      {markdown && (
        <button onClick={copy} className={buttonClasses("outline", "sm")}>
          {copied ? (
            <>
              <Check className="h-4 w-4 text-success" /> Copied
            </>
          ) : (
            <>
              <Copy className="h-4 w-4" /> Copy as Markdown
            </>
          )}
        </button>
      )}
      <button
        onClick={downloadPdf}
        disabled={pdfStatus === "generating"}
        className={buttonClasses("outline", "sm")}
      >
        {pdfStatus === "done" ? (
          <>
            <Check className="h-4 w-4 text-success" /> Downloaded
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
      {onTweak && (
        <button onClick={onTweak} className={buttonClasses("ghost", "sm")}>
          <SlidersHorizontal className="h-4 w-4" /> Tweak inputs
        </button>
      )}
      {onRegenerate && (
        <button
          onClick={onRegenerate}
          disabled={regenerating}
          className={buttonClasses("subtle", "sm")}
        >
          <RefreshCw className={regenerating ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
          Regenerate
        </button>
      )}
    </div>
  );
}
