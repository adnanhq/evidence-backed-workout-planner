import { cn } from "@/lib/utils";

export function Wordmark({
  className,
  tone = "default",
}: {
  className?: string;
  tone?: "default" | "inverted";
}) {
  return (
    <span
      className={cn(
        "font-wordmark text-[1.35rem] font-semibold leading-none tracking-tight",
        tone === "inverted" ? "text-on-dark" : "text-ink",
        className,
      )}
    >
      Axiom
    </span>
  );
}
