import type { ReactNode } from "react";
import { ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { pubmedUrl } from "@/lib/evidence";

/**
 * Superscript citation marker for display headlines. Sized in em so it never
 * blows out the 0.98 leading of `text-display`.
 */
export function Sup({
  n,
  targetId,
  className,
}: {
  n: number;
  targetId: string;
  className?: string;
}) {
  return (
    <sup>
      <a
        href={`#${targetId}`}
        aria-label={`Footnote ${n}`}
        className={cn(
          "font-mono text-[0.35em] font-medium tracking-normal text-accent-on-dark no-underline hover:underline",
          className,
        )}
      >
        {n}
      </a>
    </sup>
  );
}

export interface FootnoteItem {
  n: number;
  id: string;
  label: ReactNode;
  pmid?: string;
}

/**
 * Hairline footnote row — the ledger's citation register. Sits at the bottom
 * of the hero and the CTA band; `Sup` anchors resolve here.
 */
export function FootnoteBand({
  items,
  tone = "dark",
  aside,
  className,
}: {
  items: FootnoteItem[];
  tone?: "dark" | "light";
  /** Optional right-aligned mono line (e.g. corpus counts). */
  aside?: ReactNode;
  className?: string;
}) {
  const dark = tone === "dark";
  return (
    <div
      className={cn(
        "flex flex-col gap-3 border-t pt-5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-8",
        dark ? "border-on-dark-border" : "border-border",
        className,
      )}
    >
      <ol className="space-y-1.5">
        {items.map((item) => (
          <li
            key={item.n}
            id={item.id}
            className={cn(
              "scroll-mt-24 font-mono text-[0.72rem] leading-relaxed",
              dark ? "text-on-dark-subtle" : "text-subtle",
            )}
          >
            <span className={dark ? "text-accent-on-dark" : "text-accent"}>
              {item.n}
            </span>{" "}
            {item.label}
            {item.pmid ? (
              <>
                {" · "}
                <a
                  href={pubmedUrl(item.pmid)!}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={cn(
                    "tnum inline-flex items-center gap-0.5 whitespace-nowrap underline-offset-4 hover:underline",
                    dark
                      ? "text-on-dark-muted hover:text-accent-on-dark"
                      : "text-muted hover:text-accent",
                  )}
                >
                  PMID {item.pmid}
                  <ArrowUpRight className="h-3 w-3" aria-hidden />
                </a>
              </>
            ) : null}
          </li>
        ))}
      </ol>
      {aside ? (
        <p
          className={cn(
            "tnum shrink-0 font-mono text-[0.72rem] uppercase tracking-[0.14em]",
            dark ? "text-on-dark-subtle" : "text-subtle",
          )}
        >
          {aside}
        </p>
      ) : null}
    </div>
  );
}
