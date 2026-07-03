"use client";

import { useState } from "react";
import { Check, Copy, RefreshCw, SlidersHorizontal } from "lucide-react";
import { buttonClasses } from "@/components/ui/button";

export function ResultToolbar({
  markdown,
  onRegenerate,
  onTweak,
  regenerating,
}: {
  markdown: string;
  onRegenerate?: () => void;
  onTweak?: () => void;
  regenerating?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable */
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
