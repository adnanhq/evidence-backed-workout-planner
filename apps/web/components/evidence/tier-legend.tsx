import { cn } from "@/lib/utils";
import { EVIDENCE_TIERS, TIER_ORDER } from "@/lib/evidence";
import { EvidenceBadge } from "./evidence-badge";

export function TierLegend({ className }: { className?: string }) {
  return (
    <ul className={cn("space-y-3", className)}>
      {TIER_ORDER.map((tier) => (
        <li key={tier} className="flex items-start gap-3.5">
          <div className="w-[8.5rem] shrink-0 pt-0.5">
            <EvidenceBadge tier={tier} size="sm" />
          </div>
          <p className="text-sm leading-relaxed text-muted">
            {EVIDENCE_TIERS[tier].definition}
          </p>
        </li>
      ))}
    </ul>
  );
}
