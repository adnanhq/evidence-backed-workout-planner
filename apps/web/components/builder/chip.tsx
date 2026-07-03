import { cn } from "@/lib/utils";

export function Chip({
  selected,
  onClick,
  children,
  className,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "rounded-full border px-3 py-1.5 text-sm font-medium transition-all duration-150 ease-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 focus-visible:ring-offset-1 focus-visible:ring-offset-bg",
        selected
          ? "border-accent bg-accent-subtle text-accent"
          : "border-border bg-surface text-muted hover:border-border-strong hover:text-ink",
        className,
      )}
    >
      {children}
    </button>
  );
}
