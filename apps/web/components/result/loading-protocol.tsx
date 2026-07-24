"use client";

import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = [
  "Filtering 1,324 exercises",
  "Matching your muscles & equipment",
  "Retrieving peer-reviewed studies",
  "Ranking candidates by evidence",
  "Planning your weekly split",
];

export function LoadingProtocol() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setStep((s) => Math.min(s + 1, STEPS.length - 1));
    }, 3200);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="rounded-xl border border-border bg-surface p-6 shadow-card sm:p-8">
      <div className="flex items-center gap-2.5">
        <Loader2 className="h-5 w-5 animate-spin text-accent" />
        <h3 className="font-heading text-xl font-semibold text-ink">
          Building your evidence-based protocol
        </h3>
      </div>
      <p className="mt-1.5 text-sm text-muted">
        This can take up to a minute or two on the current model — we&apos;re reading
        the research so you don&apos;t have to.
      </p>

      <div className="mt-2 h-1 overflow-hidden rounded-full bg-surface-muted">
        <div className="h-full w-1/3 animate-pulse rounded-full bg-accent" />
      </div>

      <ol className="mt-6 space-y-3">
        {STEPS.map((label, i) => {
          const done = i < step;
          const active = i === step;
          return (
            <li key={label} className="flex items-center gap-3">
              <span
                className={cn(
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[0.7rem]",
                  done && "border-accent bg-accent text-accent-fg",
                  active && "border-accent text-accent",
                  !done && !active && "border-border text-subtle",
                )}
              >
                {done ? (
                  <Check className="h-3.5 w-3.5" />
                ) : active ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  i + 1
                )}
              </span>
              <span
                className={cn(
                  "text-sm transition-colors",
                  done && "text-muted",
                  active && "font-medium text-ink",
                  !done && !active && "text-subtle",
                )}
              >
                {label}
              </span>
            </li>
          );
        })}
      </ol>

      <div className="mt-7 space-y-3">
        {[0, 1].map((i) => (
          <div key={i} className="overflow-hidden rounded-xl border border-border">
            <div className="h-12 animate-pulse bg-surface-muted" />
            <div className="space-y-3 p-4">
              <div className="h-4 w-2/3 animate-pulse rounded bg-surface-muted" />
              <div className="h-4 w-1/2 animate-pulse rounded bg-surface-muted" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
