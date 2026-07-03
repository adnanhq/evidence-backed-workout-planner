import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 28 28"
      className={cn("h-7 w-7", className)}
      fill="none"
      aria-hidden="true"
    >
      <rect width="28" height="28" rx="8" fill="#0f766e" />
      <circle cx="14" cy="14" r="7.5" stroke="white" strokeOpacity="0.45" strokeWidth="1.4" />
      <path
        d="M9.5 14.2l3 3 6-6.4"
        stroke="white"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Wordmark({
  className,
  markClassName,
  tone = "default",
}: {
  className?: string;
  markClassName?: string;
  tone?: "default" | "inverted";
}) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark className={markClassName} />
      <span
        className={cn(
          "font-display text-[1.35rem] font-semibold leading-none tracking-tight",
          tone === "inverted" ? "text-on-dark" : "text-ink",
        )}
      >
        Protocol
      </span>
    </span>
  );
}
