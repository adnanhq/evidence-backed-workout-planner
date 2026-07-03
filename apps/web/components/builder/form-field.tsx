import { cn } from "@/lib/utils";

export function FormField({
  title,
  hint,
  aside,
  children,
  className,
}: {
  title: string;
  hint?: string;
  aside?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("rounded-xl border border-border bg-surface p-5 shadow-xs", className)}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[0.95rem] font-semibold text-ink">{title}</h3>
          {hint && <p className="mt-0.5 text-[0.82rem] leading-relaxed text-subtle">{hint}</p>}
        </div>
        {aside && <div className="shrink-0">{aside}</div>}
      </div>
      {children}
    </div>
  );
}
