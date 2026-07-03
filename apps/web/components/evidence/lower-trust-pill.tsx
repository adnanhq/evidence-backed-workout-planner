import { ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";

export function LowerTrustPill({ className }: { className?: string }) {
  return (
    <span
      title="Flagged for manual review — missing data or low retrieval confidence. Shown transparently."
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-[#f0dcb8] bg-warning-subtle px-2 py-0.5 text-[0.68rem] font-medium text-warning",
        className,
      )}
    >
      <ShieldAlert className="h-3 w-3" />
      Lower-trust
    </span>
  );
}
