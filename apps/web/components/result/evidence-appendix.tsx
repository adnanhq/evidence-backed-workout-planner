import { Library } from "lucide-react";
import { tierRank } from "@/lib/evidence";
import type { EvidenceItem } from "@/types/protocol";
import { EvidenceCard } from "@/components/evidence/evidence-card";

export function EvidenceAppendix({ items }: { items: EvidenceItem[] }) {
  if (!items.length) return null;
  const sorted = [...items].sort((a, b) => tierRank(a.tier) - tierRank(b.tier));

  return (
    <section>
      <div className="flex items-center gap-2.5">
        <Library className="h-4.5 w-4.5 text-accent" />
        <h3 className="font-display text-xl font-medium text-ink">
          The evidence behind this protocol
        </h3>
        <span className="tnum rounded-full bg-surface-muted px-2 py-0.5 text-xs text-muted">
          {items.length} studies
        </span>
      </div>
      <p className="mt-1.5 text-sm text-muted">
        Every study informing these recommendations — sorted by strength of evidence.
        Click through to read it on PubMed.
      </p>
      <div className="mt-5 grid gap-2.5 sm:grid-cols-2">
        {sorted.map((item, i) => (
          <EvidenceCard key={(item.pmid ?? "a") + i} item={item} />
        ))}
      </div>
    </section>
  );
}
