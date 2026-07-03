import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export function Section({
  children,
  className,
  innerClassName,
  id,
}: {
  children: ReactNode;
  className?: string;
  innerClassName?: string;
  id?: string;
}) {
  return (
    <section id={id} className={cn("px-5 sm:px-8", className)}>
      <div className={cn("mx-auto w-full max-w-[var(--container-page)]", innerClassName)}>
        {children}
      </div>
    </section>
  );
}

export function Eyebrow({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "text-[0.78rem] font-semibold uppercase tracking-[0.14em] text-accent",
        className,
      )}
    >
      {children}
    </p>
  );
}
