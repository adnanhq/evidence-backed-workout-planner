import { cn } from "@/lib/utils";
import { tierMeta } from "@/lib/evidence";
import type { EvidenceTier } from "@/types/protocol";

export function EvidenceBadge({
  tier,
  size = "md",
  className,
}: {
  tier: EvidenceTier | string | null | undefined;
  size?: "sm" | "md";
  className?: string;
}) {
  const meta = tierMeta(tier);
  return (
    <span
      title={meta.definition}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-medium",
        size === "sm" ? "px-2 py-0.5 text-[0.68rem]" : "px-2.5 py-1 text-xs",
        meta.badge,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", meta.dot)} aria-hidden />
      {meta.label}
    </span>
  );
}
