import { Info } from "lucide-react";

export function WarningBanner({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null;
  return (
    <div className="rounded-lg border border-[#f0dcb8] bg-warning-subtle px-4 py-3.5">
      <div className="flex gap-2.5">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
        <div>
          <p className="text-sm font-medium text-warning">
            A few honest notes on this plan
          </p>
          <ul className="mt-1.5 space-y-1 text-[0.83rem] leading-relaxed text-[#7a5518]">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
