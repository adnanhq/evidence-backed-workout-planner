"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

/** Planning caveats, folded into a quiet one-line disclosure. */
export function WarningBanner({ warnings }: { warnings: string[] }) {
  const [open, setOpen] = useState(false);
  if (!warnings.length) return null;

  return (
    <div className="rounded-xl border border-border bg-surface">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2.5 px-4 py-3 text-left"
      >
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-warning" aria-hidden />
        <span className="text-[0.83rem] font-medium text-muted">
          {warnings.length} planning {warnings.length === 1 ? "note" : "notes"} on this
          protocol
        </span>
        <ChevronDown
          className={cn(
            "ml-auto h-4 w-4 shrink-0 text-subtle transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>
      {open && (
        <ul className="space-y-1.5 border-t border-border px-4 py-3 text-[0.83rem] leading-relaxed text-muted">
          {warnings.map((w, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-subtle" aria-hidden>
                —
              </span>
              {w}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
