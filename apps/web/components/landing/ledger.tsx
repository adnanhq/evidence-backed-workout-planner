import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Numbered section heading for the landing "ledger": a mono index + uppercase
 * label on a hairline rule, then a display headline. Landing-local — other
 * pages keep using `Eyebrow`.
 */
export function LedgerHeading({
  index,
  label,
  title,
  tone = "light",
  children,
  className,
}: {
  index: string;
  label: string;
  title: ReactNode;
  tone?: "light" | "dark";
  /** Optional lede paragraph rendered under the headline. */
  children?: ReactNode;
  className?: string;
}) {
  const dark = tone === "dark";
  return (
    <div className={className}>
      <div className="flex items-baseline gap-4">
        <span
          className={cn(
            "tnum font-mono text-[0.78rem] font-medium",
            dark ? "text-accent-on-dark" : "text-accent",
          )}
        >
          {index}
        </span>
        <span
          className={cn(
            "font-mono text-[0.7rem] uppercase tracking-[0.18em]",
            dark ? "text-on-dark-subtle" : "text-subtle",
          )}
        >
          {label}
        </span>
        <span
          aria-hidden
          className={cn(
            "flex-1 border-t",
            dark ? "border-on-dark-border" : "border-border",
          )}
        />
      </div>
      <h2
        className={cn(
          "mt-6 max-w-3xl font-heading text-display-2",
          dark ? "text-on-dark" : "text-ink",
        )}
      >
        {title}
      </h2>
      {children ? (
        <div
          className={cn(
            "mt-4 max-w-2xl text-[0.98rem] leading-relaxed",
            dark ? "text-on-dark-muted" : "text-muted",
          )}
        >
          {children}
        </div>
      ) : null}
    </div>
  );
}
