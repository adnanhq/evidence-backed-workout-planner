import { ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { tierMeta } from "@/lib/evidence";
import type { EvidenceItem } from "@/types/protocol";

export function CitationChip({ item }: { item: EvidenceItem }) {
  const meta = tierMeta(item.tier);
  if (!item.url || !item.pmid) return null;
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      title={item.title ?? undefined}
      className={cn(
        "group inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[0.72rem] font-medium transition-shadow hover:shadow-sm",
        meta.badge,
      )}
    >
      <span>{meta.short}</span>
      <span className="opacity-50">·</span>
      <span className="tnum">PMID {item.pmid}</span>
      <ArrowUpRight className="h-3 w-3 opacity-60 transition-opacity group-hover:opacity-100" />
    </a>
  );
}
