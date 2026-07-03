import { ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EvidenceItem } from "@/types/protocol";
import { EvidenceBadge } from "./evidence-badge";
import { LowerTrustPill } from "./lower-trust-pill";

export function EvidenceCard({
  item,
  className,
}: {
  item: EvidenceItem;
  className?: string;
}) {
  return (
    <div className={cn("rounded-lg border border-border bg-surface p-3.5", className)}>
      <div className="flex flex-wrap items-center gap-2">
        <EvidenceBadge tier={item.tier} size="sm" />
        {item.trustLabel === "lower-trust" && <LowerTrustPill />}
        {item.year != null && (
          <span className="tnum text-xs text-subtle">{item.year}</span>
        )}
      </div>
      {item.title && (
        <p className="mt-2 text-sm font-medium leading-snug text-ink">{item.title}</p>
      )}
      {item.snippet && (
        <p className="mt-1.5 text-[0.83rem] leading-relaxed text-muted">{item.snippet}</p>
      )}
      {item.url && (
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2.5 inline-flex items-center gap-1 text-[0.8rem] font-medium text-accent hover:text-accent-hover"
        >
          View on PubMed <ArrowUpRight className="h-3.5 w-3.5" />
        </a>
      )}
    </div>
  );
}
